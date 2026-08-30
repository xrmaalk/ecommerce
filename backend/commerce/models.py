import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from catalog.models import Product


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONVERTED = "converted", "Converted"
        ABANDONED = "abandoned", "Abandoned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="carts", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    currency = models.CharField(max_length=3, default="CAD", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user",),
                condition=Q(status="active"),
                name="one_active_cart_per_customer",
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.status} cart"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="cart_items", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=(MinValueValidator(1),))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(fields=("cart", "product"), name="unique_product_per_cart"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="cart_item_quantity_gte_1"),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product}"


class ShippingRate(models.Model):
    class Country(models.TextChoices):
        CANADA = "CA", "Canada"
        UNITED_STATES = "US", "United States"

    country_code = models.CharField(max_length=2, choices=Country.choices, unique=True)
    name = models.CharField(max_length=80, default="Standard shipping")
    amount_cad = models.DecimalField(max_digits=9, decimal_places=2, validators=(MinValueValidator(0),))
    estimated_days_min = models.PositiveSmallIntegerField(default=3)
    estimated_days_max = models.PositiveSmallIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("country_code",)

    def __str__(self):
        return f"{self.get_country_code_display()} — ${self.amount_cad} CAD"


def checkout_expiry():
    return timezone.now() + timedelta(minutes=30)


class CheckoutSession(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PAYPAL_CREATED = "paypal_created", "PayPal order created"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="checkout_sessions", on_delete=models.PROTECT)
    cart = models.ForeignKey(Cart, related_name="checkout_sessions", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    currency = models.CharField(max_length=3, default="CAD", editable=False)
    shipping_address = models.JSONField(default=dict)
    line_items = models.JSONField(default=list)
    subtotal_cad = models.DecimalField(max_digits=11, decimal_places=2)
    shipping_cad = models.DecimalField(max_digits=11, decimal_places=2)
    tax_cad = models.DecimalField(max_digits=11, decimal_places=2)
    total_cad = models.DecimalField(max_digits=11, decimal_places=2)
    tax_provider = models.CharField(max_length=80, blank=True)
    tax_reference = models.CharField(max_length=160, blank=True)
    paypal_order_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    inventory_reserved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=checkout_expiry)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Checkout {self.id} — {self.status}"


def order_number():
    return f"OE-{uuid.uuid4().hex[:12].upper()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=20, unique=True, default=order_number, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.PROTECT)
    checkout_session = models.OneToOneField(CheckoutSession, related_name="order", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PAID)
    currency = models.CharField(max_length=3, default="CAD", editable=False)
    customer_email = models.EmailField()
    shipping_address = models.JSONField(default=dict)
    subtotal_cad = models.DecimalField(max_digits=11, decimal_places=2)
    shipping_cad = models.DecimalField(max_digits=11, decimal_places=2)
    tax_cad = models.DecimalField(max_digits=11, decimal_places=2)
    total_cad = models.DecimalField(max_digits=11, decimal_places=2)
    paypal_order_id = models.CharField(max_length=80, unique=True)
    paypal_capture_id = models.CharField(max_length=80, unique=True)
    paid_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.SET_NULL, null=True, blank=True)
    sku = models.CharField(max_length=80)
    name = models.CharField(max_length=180)
    quantity = models.PositiveIntegerField(validators=(MinValueValidator(1),))
    unit_price_cad = models.DecimalField(max_digits=10, decimal_places=2)
    line_total_cad = models.DecimalField(max_digits=11, decimal_places=2)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.quantity} × {self.name}"


class PaymentWebhookEvent(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        VERIFIED = "verified", "Verified"
        PROCESSED = "processed", "Processed"
        IGNORED = "ignored", "Ignored"
        FAILED = "failed", "Failed"

    provider = models.CharField(max_length=20, default="paypal", editable=False)
    external_id = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=100)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    payload = models.JSONField(default=dict)
    processing_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-received_at",)

    def __str__(self):
        return f"{self.event_type} — {self.external_id}"


class ImportJob(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    source_name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-started_at",)

    def __str__(self):
        return f"{self.source_name} — {self.status}"
