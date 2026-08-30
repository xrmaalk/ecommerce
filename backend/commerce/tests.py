import json
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, Product

from .models import Cart, CheckoutSession, Order, PaymentWebhookEvent, ShippingRate
from .paypal import PayPalError
from .services import CommerceError, complete_checkout, create_checkout_session, create_paypal_order

User = get_user_model()
ZERO_TAX = override_settings(
    COMMERCE_TAX_ADAPTER="commerce.tax.ZeroTaxAdapter",
    COMMERCE_ALLOW_ZERO_TAX=True,
)


def make_product(sku="OE-001", inventory=10, price="20.00"):
    category, _ = Category.objects.get_or_create(name="Body Care", slug="body-care")
    return Product.objects.create(
        name=f"Product {sku}",
        slug=sku.lower(),
        sku=sku,
        category=category,
        price_cad=price,
        inventory_quantity=inventory,
    )


class FakePayPalClient:
    def create_order(self, payload, request_id):
        self.payload = payload
        self.request_id = request_id
        return {"id": "PAYPAL-ORDER-1", "status": "CREATED"}

    def capture_order(self, paypal_order_id, request_id):
        return {
            "id": paypal_order_id,
            "status": "COMPLETED",
            "payer": {"email_address": "payer@example.com"},
            "purchase_units": [{"payments": {"captures": [{
                "id": "CAPTURE-1",
                "status": "COMPLETED",
                "amount": {"currency_code": "CAD", "value": "27.00"},
            }]}}],
        }


class CommerceApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="shopper@example.com", email="shopper@example.com", password="StrongPass!2026"
        )
        self.other_user = User.objects.create_user(
            username="other@example.com", email="other@example.com", password="StrongPass!2026"
        )
        self.product = make_product()
        ShippingRate.objects.update_or_create(
            country_code="CA", defaults={"amount_cad": "7.00", "is_active": True}
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.user)

    def address(self):
        return {
            "first_name": "Avery", "last_name": "Stone", "address_line_1": "10 Main Street",
            "address_line_2": "", "city": "Calgary", "region": "AB", "postal_code": "T2P 1J9",
            "country_code": "CA", "phone": "",
        }

    def add_product(self, quantity=2):
        return self.client.put(
            reverse("commerce:cart-item"),
            {"product_id": self.product.id, "quantity": quantity},
            format="json",
        )

    def test_cart_requires_authentication(self):
        response = self.client.get(reverse("commerce:cart"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cart_item_uses_server_price_and_inventory_limit(self):
        self.authenticate()
        response = self.add_product(quantity=99)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"][0]["quantity"], 10)
        self.assertEqual(response.data["subtotal_cad"], "200.00")

    def test_cart_merge_is_idempotent_and_preserves_larger_server_quantity(self):
        self.authenticate()
        self.add_product(quantity=4)
        payload = {"items": [{"product_id": self.product.id, "quantity": 2}]}
        first = self.client.post(reverse("commerce:cart-merge"), payload, format="json")
        second = self.client.post(reverse("commerce:cart-merge"), payload, format="json")
        self.assertEqual(first.data["items"][0]["quantity"], 4)
        self.assertEqual(second.data["items"][0]["quantity"], 4)

    def test_checkout_is_blocked_while_tax_provider_is_unavailable(self):
        self.authenticate()
        self.add_product()
        response = self.client.post(reverse("commerce:checkout-quote"), self.address(), format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("not configured", response.data["detail"])

    @ZERO_TAX
    def test_checkout_quote_uses_flat_shipping_and_server_totals(self):
        self.authenticate()
        self.add_product()
        response = self.client.post(reverse("commerce:checkout-quote"), self.address(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["subtotal_cad"], "40.00")
        self.assertEqual(response.data["shipping_cad"], "7.00")
        self.assertEqual(response.data["tax_cad"], "0.00")
        self.assertEqual(response.data["total_cad"], "47.00")

    @ZERO_TAX
    def test_paypal_payload_contains_authoritative_breakdown(self):
        self.authenticate()
        self.add_product(quantity=1)
        checkout = create_checkout_session(self.user, self.address())
        fake = FakePayPalClient()
        paypal_id = create_paypal_order(checkout, client=fake)
        self.assertEqual(paypal_id, "PAYPAL-ORDER-1")
        amount = fake.payload["purchase_units"][0]["amount"]
        self.assertEqual(amount["value"], "27.00")
        self.assertEqual(amount["breakdown"]["tax_total"]["value"], "0.00")
        self.product.refresh_from_db()
        checkout.refresh_from_db()
        self.assertEqual(self.product.inventory_quantity, 9)
        self.assertIsNotNone(checkout.inventory_reserved_at)

    @ZERO_TAX
    def test_paypal_failure_releases_inventory_reservation(self):
        class FailingClient:
            def create_order(self, payload, request_id):
                raise PayPalError("PayPal unavailable")

        self.authenticate()
        self.add_product(quantity=2)
        checkout = create_checkout_session(self.user, self.address())
        with self.assertRaises(PayPalError):
            create_paypal_order(checkout, client=FailingClient())
        self.product.refresh_from_db()
        checkout.refresh_from_db()
        self.assertEqual(self.product.inventory_quantity, 10)
        self.assertIsNone(checkout.inventory_reserved_at)

    @ZERO_TAX
    def test_expired_reservation_release_command_restores_inventory(self):
        self.authenticate()
        self.add_product(quantity=3)
        checkout = create_checkout_session(self.user, self.address())
        create_paypal_order(checkout, client=FakePayPalClient())
        CheckoutSession.objects.filter(pk=checkout.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        call_command("release_expired_checkout_reservations")
        self.product.refresh_from_db()
        checkout.refresh_from_db()
        self.assertEqual(self.product.inventory_quantity, 10)
        self.assertEqual(checkout.status, CheckoutSession.Status.EXPIRED)

    @ZERO_TAX
    def test_completed_capture_creates_immutable_order_and_decrements_stock(self):
        self.authenticate()
        self.add_product(quantity=2)
        checkout = create_checkout_session(self.user, self.address())
        checkout.paypal_order_id = "PAYPAL-ORDER-1"
        checkout.save(update_fields=("paypal_order_id",))
        order = complete_checkout(
            checkout.id,
            capture_id="CAPTURE-1",
            amount_value="47.00",
            currency_code="CAD",
            payer_email="payer@example.com",
        )
        self.product.refresh_from_db()
        checkout.refresh_from_db()
        self.assertEqual(order.items.get().sku, self.product.sku)
        self.assertEqual(order.customer_email, "payer@example.com")
        self.assertEqual(self.product.inventory_quantity, 8)
        self.assertEqual(checkout.cart.status, Cart.Status.CONVERTED)
        repeated = complete_checkout(
            checkout.id, capture_id="CAPTURE-1", amount_value="47.00", currency_code="CAD"
        )
        self.product.refresh_from_db()
        self.assertEqual(repeated.pk, order.pk)
        self.assertEqual(self.product.inventory_quantity, 8)

    @ZERO_TAX
    def test_mismatched_capture_total_is_rejected(self):
        self.authenticate()
        self.add_product(quantity=1)
        checkout = create_checkout_session(self.user, self.address())
        checkout.paypal_order_id = "PAYPAL-ORDER-2"
        checkout.save(update_fields=("paypal_order_id",))
        with self.assertRaises(CommerceError):
            complete_checkout(
                checkout.id, capture_id="CAPTURE-2", amount_value="1.00", currency_code="CAD"
            )
        self.assertFalse(Order.objects.filter(checkout_session=checkout).exists())

    def test_customer_cannot_read_another_customers_order(self):
        self.authenticate(self.other_user)
        response = self.client.get(reverse("commerce:order-detail", args=("OE-NOT-THEIRS",)))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("commerce.views.PayPalClient")
    def test_webhook_signature_failure_is_recorded(self, client_class):
        client_class.return_value.verify_webhook.return_value = False
        event = {"id": "WH-1", "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {}}
        response = self.client.post(
            reverse("commerce:paypal-webhook"),
            data=json.dumps(event),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PaymentWebhookEvent.objects.get(external_id="WH-1").status, "failed")

    @patch("commerce.views.PayPalClient")
    def test_irrelevant_verified_webhook_is_idempotently_ignored(self, client_class):
        client_class.return_value.verify_webhook.return_value = True
        event = {"id": "WH-2", "event_type": "CHECKOUT.ORDER.APPROVED", "resource": {}}
        first = self.client.post(reverse("commerce:paypal-webhook"), data=json.dumps(event), content_type="application/json")
        second = self.client.post(reverse("commerce:paypal-webhook"), data=json.dumps(event), content_type="application/json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(PaymentWebhookEvent.objects.filter(external_id="WH-2").count(), 1)


class WooCommerceImportTests(TestCase):
    def write_csv(self, directory):
        path = Path(directory) / "products.csv"
        path.write_text(
            "SKU,Name,Slug,Categories,Regular price,Sale price,Stock,In stock?,Published,Is featured?,Description\n"
            "WOO-1,Daily Moisture,daily-moisture,Body Care,25.00,20.00,12,1,1,1,Hydrating care\n",
            encoding="utf-8",
        )
        return path

    def test_dry_run_rolls_back_all_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory)
            call_command("import_woocommerce_csv", path, dry_run=True)
        self.assertFalse(Product.objects.filter(sku="WOO-1").exists())

    def test_repeat_import_updates_instead_of_duplicating(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory)
            call_command("import_woocommerce_csv", path)
            call_command("import_woocommerce_csv", path)
        product = Product.objects.get(sku="WOO-1")
        self.assertEqual(Product.objects.filter(sku="WOO-1").count(), 1)
        self.assertEqual(product.price_cad, Decimal("20.00"))
        self.assertEqual(product.compare_at_price_cad, Decimal("25.00"))

    def test_invalid_row_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            path.write_text("SKU,Name\n,Missing SKU\n", encoding="utf-8")
            with self.assertRaises(CommandError):
                call_command("import_woocommerce_csv", path)
