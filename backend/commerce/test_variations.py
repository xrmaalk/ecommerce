from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from catalog.models import ProductVariant
from .models import CartItem, ShippingRate
from .services import InventoryError, complete_checkout, create_checkout_session, create_paypal_order, get_active_cart, release_inventory_reservation, reserve_inventory, set_cart_item
from .tests import FakePayPalClient, make_product


@override_settings(COMMERCE_TAX_ADAPTER="commerce.tax.ZeroTaxAdapter", COMMERCE_ALLOW_ZERO_TAX=True)
class ProductVariationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="variant-shopper", email="variants@example.com")
        self.client.force_authenticate(self.user)
        self.product = make_product()
        self.small = ProductVariant.objects.create(product=self.product, sku="SMALL-BLACK", size="Small", color="Black", price_cad="22.00", inventory_quantity=3)
        self.large = ProductVariant.objects.create(product=self.product, sku="LARGE-BLACK", size="Large", color="Black", inventory_quantity=5)
        ShippingRate.objects.update_or_create(country_code="CA", defaults={"amount_cad": "7.00", "is_active": True})
        self.address = {"first_name": "Avery", "last_name": "Stone", "address_line_1": "10 Main Street", "city": "Calgary", "region": "AB", "postal_code": "T2P 1J9", "country_code": "CA"}

    def put(self, variant=None, quantity=1, product=None):
        return self.client.put(reverse("commerce:cart-item"), {"product_id": (product or self.product).id, "variant_id": variant.id if variant else None, "quantity": quantity}, format="json")

    def test_catalog_exposes_active_variations_and_effective_prices(self):
        self.small.is_active = False
        self.small.save()
        response = self.client.get(reverse("product-detail", args=(self.product.slug,)))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["has_variants"])
        self.assertEqual([row["id"] for row in response.data["variants"]], [self.large.id])
        self.assertEqual(response.data["variants"][0]["price_cad"], "20.00")
        self.large.is_active = False
        self.large.save()
        response = self.client.get(reverse("product-detail", args=(self.product.slug,)))
        self.assertTrue(response.data["has_variants"])
        self.assertFalse(response.data["in_stock"])

    def test_cart_preserves_distinct_combinations_and_uses_server_prices(self):
        self.assertEqual(self.put(self.small, 99).status_code, 200)
        response = self.put(self.large, 2)
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(response.data["subtotal_cad"], "106.00")
        self.assertEqual(response.data["items"][0]["quantity"], 3)
        self.assertEqual(response.data["items"][0]["variant"]["sku"], "SMALL-BLACK")
        self.put(self.small, 0)
        self.assertEqual(get_active_cart(self.user).items.get().variant_id, self.large.id)

    def test_rejects_missing_wrong_product_inactive_and_sold_out_variations(self):
        self.assertEqual(self.put().status_code, 400)
        other = make_product(sku="OTHER")
        self.assertEqual(self.put(self.small, product=other).status_code, 400)
        self.small.is_active = False
        self.small.save()
        self.assertEqual(self.put(self.small).status_code, 400)
        self.large.inventory_quantity = 0
        self.large.save()
        self.assertEqual(self.put(self.large).status_code, 400)
        self.assertFalse(get_active_cart(self.user).items.exists())

    def test_merge_is_idempotent_per_combination(self):
        self.put(self.small, 2)
        payload = {"items": [{"product_id": self.product.id, "variant_id": self.small.id, "quantity": 1}, {"product_id": self.product.id, "variant_id": self.large.id, "quantity": 3}]}
        for _ in range(2):
            response = self.client.post(reverse("commerce:cart-merge"), payload, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual([item["quantity"] for item in response.data["items"]], [2, 3])
        payload["items"].append(payload["items"][0])
        self.assertEqual(self.client.post(reverse("commerce:cart-merge"), payload, format="json").status_code, 400)

    def test_database_prevents_duplicate_base_and_variation_lines(self):
        cart = get_active_cart(self.user)
        set_cart_item(self.user, self.product, 1, self.small.id)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=cart, product=self.product, variant=self.small, quantity=1)
        base = make_product(sku="BASE")
        set_cart_item(self.user, base, 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=cart, product=base, quantity=1)

    def test_variant_admin_validation_requires_options_and_unique_base_sku(self):
        empty = ProductVariant(product=self.product, sku="NEW")
        with self.assertRaises(ValidationError):
            empty.full_clean()
        empty.size = "Medium"
        empty.sku = self.product.sku
        with self.assertRaises(ValidationError):
            empty.full_clean()

    def test_checkout_and_paypal_use_selected_price_sku_and_description(self):
        self.put(self.small, 2)
        self.put(self.large, 1)
        checkout = create_checkout_session(self.user, self.address)
        self.assertEqual(checkout.subtotal_cad, Decimal("64.00"))
        self.assertEqual(checkout.line_items[0]["variation"], "Size: Small / Color: Black")
        fake = FakePayPalClient()
        create_paypal_order(checkout, client=fake)
        items = fake.payload["purchase_units"][0]["items"]
        self.assertEqual(items[0]["sku"], "SMALL-BLACK")
        self.assertIn("Size: Small", items[0]["name"])
        self.small.refresh_from_db()
        self.large.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual((self.small.inventory_quantity, self.large.inventory_quantity, self.product.inventory_quantity), (1, 4, 10))
        release_inventory_reservation(checkout.id)
        release_inventory_reservation(checkout.id)
        self.small.refresh_from_db()
        self.large.refresh_from_db()
        self.assertEqual((self.small.inventory_quantity, self.large.inventory_quantity), (3, 5))

    def test_order_variation_is_immutable_and_stock_is_decremented_once(self):
        self.put(self.small, 2)
        checkout = create_checkout_session(self.user, self.address)
        create_paypal_order(checkout, client=FakePayPalClient())
        self.small.size = "Changed later"
        self.small.save(update_fields=("size",))
        order = complete_checkout(checkout.id, capture_id="VARIANT-CAPTURE", amount_value="51.00", currency_code="CAD")
        repeated = complete_checkout(checkout.id, capture_id="VARIANT-CAPTURE", amount_value="51.00", currency_code="CAD")
        self.assertEqual(order.pk, repeated.pk)
        self.assertEqual(order.items.get().variation, "Size: Small / Color: Black")
        self.assertEqual(order.items.get().unit_price_cad, Decimal("22.00"))
        self.small.refresh_from_db()
        self.assertEqual(self.small.inventory_quantity, 1)
        response = self.client.get(reverse("commerce:order-detail", args=(order.number,)))
        self.assertEqual(response.data["items"][0]["variation"], "Size: Small / Color: Black")

    def test_stock_change_after_quote_rolls_back_all_reservations(self):
        self.put(self.small, 2)
        self.put(self.large, 2)
        checkout = create_checkout_session(self.user, self.address)
        self.large.inventory_quantity = 1
        self.large.save()
        with self.assertRaises(InventoryError):
            reserve_inventory(checkout.id)
        self.small.refresh_from_db()
        self.assertEqual(self.small.inventory_quantity, 3)

    def test_unlimited_variation_and_capture_without_prior_reservation(self):
        self.small.track_inventory = False
        self.small.inventory_quantity = 0
        self.small.save()
        response = self.put(self.small, 4)
        self.assertEqual(response.status_code, 200)
        checkout = create_checkout_session(self.user, self.address)
        checkout.paypal_order_id = "UNLIMITED-PAYPAL"
        checkout.save()
        order = complete_checkout(checkout.id, capture_id="UNLIMITED-CAPTURE", amount_value="95.00", currency_code="CAD")
        self.assertEqual(order.items.get().quantity, 4)
        self.small.refresh_from_db()
        self.assertEqual(self.small.inventory_quantity, 0)
