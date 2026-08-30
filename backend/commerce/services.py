from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from catalog.models import Product

from .models import Cart, CartItem, CheckoutSession, Order, OrderItem, ShippingRate
from .paypal import PayPalClient, PayPalError
from .tax import get_tax_adapter

CENT = Decimal("0.01")


class CommerceError(Exception):
    pass


class InventoryError(CommerceError):
    pass


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def money_string(value):
    return f"{money(value):.2f}"


def get_active_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user, status=Cart.Status.ACTIVE)
    return cart


def cart_queryset():
    return Cart.objects.prefetch_related("items__product__images", "items__product__category")


def set_cart_item(user, product, quantity):
    cart = get_active_cart(user)
    if quantity <= 0:
        CartItem.objects.filter(cart=cart, product=product).delete()
        return cart_queryset().get(pk=cart.pk)
    if not product.is_active:
        raise CommerceError("This product is not available.")
    maximum = product.inventory_quantity if product.track_inventory else 99
    if product.track_inventory and maximum < 1:
        raise InventoryError(f"{product.name} is out of stock.")
    quantity = min(int(quantity), maximum, 99)
    CartItem.objects.update_or_create(cart=cart, product=product, defaults={"quantity": quantity})
    return cart_queryset().get(pk=cart.pk)


@transaction.atomic
def merge_cart(user, items):
    cart = get_active_cart(user)
    products = Product.objects.filter(id__in=[item["product_id"] for item in items], is_active=True)
    product_map = {product.id: product for product in products}
    existing = {item.product_id: item for item in cart.items.select_for_update()}
    for incoming in items:
        product = product_map.get(incoming["product_id"])
        if not product:
            continue
        maximum = product.inventory_quantity if product.track_inventory else 99
        if maximum < 1:
            continue
        quantity = min(max(incoming["quantity"], existing.get(product.id).quantity if product.id in existing else 0), maximum, 99)
        CartItem.objects.update_or_create(cart=cart, product=product, defaults={"quantity": quantity})
    return cart_queryset().get(pk=cart.pk)


def snapshot_cart(cart):
    items = []
    subtotal = Decimal("0.00")
    cart_items = cart.items.select_related("product").order_by("id")
    if not cart_items.exists():
        raise CommerceError("Your cart is empty.")
    for cart_item in cart_items:
        product = cart_item.product
        if not product.is_active:
            raise CommerceError(f"{product.name} is no longer available.")
        if product.track_inventory and cart_item.quantity > product.inventory_quantity:
            raise InventoryError(f"Only {product.inventory_quantity} of {product.name} remain in stock.")
        unit_price = money(product.price_cad)
        line_total = money(unit_price * cart_item.quantity)
        subtotal += line_total
        items.append({
            "product_id": product.id,
            "sku": product.sku,
            "name": product.name,
            "quantity": cart_item.quantity,
            "unit_price_cad": money_string(unit_price),
            "line_total_cad": money_string(line_total),
        })
    return items, money(subtotal)


def calculate_checkout(cart, address):
    line_items, subtotal = snapshot_cart(cart)
    country_code = address["country_code"]
    try:
        shipping_rate = ShippingRate.objects.get(country_code=country_code, is_active=True)
    except ShippingRate.DoesNotExist as error:
        raise CommerceError("Shipping is not configured for this destination yet.") from error
    shipping = money(shipping_rate.amount_cad)
    tax_quote = get_tax_adapter().calculate(
        subtotal=subtotal,
        shipping=shipping,
        address=address,
        items=line_items,
    )
    tax = money(tax_quote.amount)
    return {
        "line_items": line_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": money(subtotal + shipping + tax),
        "tax_provider": tax_quote.provider,
        "tax_reference": tax_quote.reference,
    }


def create_checkout_session(user, address):
    cart = get_active_cart(user)
    totals = calculate_checkout(cart, address)
    CheckoutSession.objects.filter(
        user=user,
        cart=cart,
        status=CheckoutSession.Status.OPEN,
    ).update(status=CheckoutSession.Status.EXPIRED)
    return CheckoutSession.objects.create(
        user=user,
        cart=cart,
        shipping_address=address,
        line_items=totals["line_items"],
        subtotal_cad=totals["subtotal"],
        shipping_cad=totals["shipping"],
        tax_cad=totals["tax"],
        total_cad=totals["total"],
        tax_provider=totals["tax_provider"],
        tax_reference=totals["tax_reference"],
    )


def paypal_order_payload(session):
    amount = {
        "currency_code": "CAD",
        "value": money_string(session.total_cad),
        "breakdown": {
            "item_total": {"currency_code": "CAD", "value": money_string(session.subtotal_cad)},
            "shipping": {"currency_code": "CAD", "value": money_string(session.shipping_cad)},
            "tax_total": {"currency_code": "CAD", "value": money_string(session.tax_cad)},
        },
    }
    items = [{
        "name": item["name"][:127],
        "sku": item["sku"][:127],
        "quantity": str(item["quantity"]),
        "unit_amount": {"currency_code": "CAD", "value": item["unit_price_cad"]},
        "category": "PHYSICAL_GOODS",
    } for item in session.line_items]
    address = session.shipping_address
    shipping = {
        "name": {"full_name": f"{address['first_name']} {address['last_name']}".strip()},
        "address": {
            "address_line_1": address["address_line_1"],
            "admin_area_2": address["city"],
            "admin_area_1": address["region"],
            "postal_code": address["postal_code"],
            "country_code": address["country_code"],
        },
    }
    if address.get("address_line_2"):
        shipping["address"]["address_line_2"] = address["address_line_2"]
    return {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": str(session.id),
            "custom_id": str(session.id),
            "invoice_id": str(session.idempotency_key),
            "amount": amount,
            "items": items,
            "shipping": shipping,
        }],
        "payment_source": {"paypal": {"experience_context": {
            "shipping_preference": "SET_PROVIDED_ADDRESS",
            "user_action": "PAY_NOW",
        }}},
    }


@transaction.atomic
def reserve_inventory(session_id):
    session = CheckoutSession.objects.select_for_update().get(pk=session_id)
    if session.inventory_reserved_at:
        return session
    product_ids = [item["product_id"] for item in session.line_items]
    products = Product.objects.select_for_update().filter(id__in=product_ids)
    product_map = {product.id: product for product in products}
    for item in session.line_items:
        product = product_map.get(item["product_id"])
        if not product or not product.is_active:
            raise InventoryError(f"{item['name']} is no longer available.")
        if product.track_inventory and product.inventory_quantity < item["quantity"]:
            raise InventoryError(f"Only {product.inventory_quantity} of {product.name} remain in stock.")
    for item in session.line_items:
        product = product_map[item["product_id"]]
        if product.track_inventory:
            product.inventory_quantity -= item["quantity"]
            product.save(update_fields=("inventory_quantity", "updated_at"))
    session.inventory_reserved_at = timezone.now()
    session.save(update_fields=("inventory_reserved_at", "updated_at"))
    return session


@transaction.atomic
def release_inventory_reservation(session_id):
    session = CheckoutSession.objects.select_for_update().get(pk=session_id)
    if not session.inventory_reserved_at or session.status == CheckoutSession.Status.COMPLETED:
        return session
    product_ids = [item["product_id"] for item in session.line_items]
    products = Product.objects.select_for_update().filter(id__in=product_ids)
    product_map = {product.id: product for product in products}
    for item in session.line_items:
        product = product_map.get(item["product_id"])
        if product and product.track_inventory:
            product.inventory_quantity += item["quantity"]
            product.save(update_fields=("inventory_quantity", "updated_at"))
    session.inventory_reserved_at = None
    session.status = CheckoutSession.Status.EXPIRED
    session.save(update_fields=("inventory_reserved_at", "status", "updated_at"))
    return session


def create_paypal_order(session, client=None):
    if session.status == CheckoutSession.Status.COMPLETED:
        raise CommerceError("This checkout is already complete.")
    if session.expires_at <= timezone.now():
        session.status = CheckoutSession.Status.EXPIRED
        session.save(update_fields=("status", "updated_at"))
        raise CommerceError("This checkout quote has expired. Please calculate a new total.")
    if session.paypal_order_id:
        return session.paypal_order_id
    client = client or PayPalClient()
    session = reserve_inventory(session.id)
    try:
        response = client.create_order(paypal_order_payload(session), session.idempotency_key)
    except Exception:
        release_inventory_reservation(session.id)
        raise
    paypal_order_id = response.get("id")
    if not paypal_order_id:
        release_inventory_reservation(session.id)
        raise PayPalError("PayPal did not return an order ID.")
    session.paypal_order_id = paypal_order_id
    session.status = CheckoutSession.Status.PAYPAL_CREATED
    session.save(update_fields=("paypal_order_id", "status", "updated_at"))
    return paypal_order_id


def extract_capture(response):
    try:
        capture = response["purchase_units"][0]["payments"]["captures"][0]
    except (KeyError, IndexError, TypeError) as error:
        raise PayPalError("PayPal capture details were incomplete.") from error
    if response.get("status") != "COMPLETED" or capture.get("status") != "COMPLETED":
        raise PayPalError("PayPal did not complete the payment.")
    payer_email = response.get("payer", {}).get("email_address", "")
    return capture, payer_email


@transaction.atomic
def complete_checkout(session_id, *, capture_id, amount_value, currency_code, payer_email=""):
    session = CheckoutSession.objects.select_for_update().select_related("cart", "user").get(pk=session_id)
    try:
        return session.order
    except Order.DoesNotExist:
        pass
    if not capture_id:
        raise CommerceError("PayPal did not provide a capture ID.")
    if currency_code != "CAD" or money(amount_value) != money(session.total_cad):
        raise CommerceError("The captured PayPal amount does not match the checkout total.")

    product_ids = [item["product_id"] for item in session.line_items]
    products = Product.objects.select_for_update().filter(id__in=product_ids)
    product_map = {product.id: product for product in products}
    for item in session.line_items:
        product = product_map.get(item["product_id"])
        if not product:
            raise InventoryError(f"{item['name']} is no longer available.")
        if product.track_inventory and not session.inventory_reserved_at:
            if product.inventory_quantity < item["quantity"]:
                raise InventoryError(f"Only {product.inventory_quantity} of {product.name} remain in stock.")
            product.inventory_quantity -= item["quantity"]
            product.save(update_fields=("inventory_quantity", "updated_at"))

    order = Order.objects.create(
        user=session.user,
        checkout_session=session,
        customer_email=payer_email or session.user.email,
        shipping_address=session.shipping_address,
        subtotal_cad=session.subtotal_cad,
        shipping_cad=session.shipping_cad,
        tax_cad=session.tax_cad,
        total_cad=session.total_cad,
        paypal_order_id=session.paypal_order_id,
        paypal_capture_id=capture_id,
        paid_at=timezone.now(),
    )
    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            product=product_map.get(item["product_id"]),
            sku=item["sku"],
            name=item["name"],
            quantity=item["quantity"],
            unit_price_cad=item["unit_price_cad"],
            line_total_cad=item["line_total_cad"],
        ) for item in session.line_items
    ])
    session.status = CheckoutSession.Status.COMPLETED
    session.save(update_fields=("status", "updated_at"))
    session.cart.status = Cart.Status.CONVERTED
    session.cart.save(update_fields=("status", "updated_at"))
    return order


def capture_checkout(session, client=None):
    if not session.paypal_order_id:
        raise CommerceError("No PayPal order exists for this checkout.")
    if session.expires_at <= timezone.now() and session.status != CheckoutSession.Status.COMPLETED:
        raise CommerceError("This PayPal checkout has expired. Please calculate a new total.")
    client = client or PayPalClient()
    response = client.capture_order(session.paypal_order_id, f"capture-{session.idempotency_key}")
    capture, payer_email = extract_capture(response)
    amount = capture.get("amount", {})
    return complete_checkout(
        session.id,
        capture_id=capture["id"],
        amount_value=amount.get("value", "0"),
        currency_code=amount.get("currency_code", ""),
        payer_email=payer_email,
    )
