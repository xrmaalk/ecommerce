from django.contrib import admin

from .models import (
    Cart,
    CartItem,
    CheckoutSession,
    ImportJob,
    Order,
    OrderItem,
    PaymentWebhookEvent,
    ShippingRate,
)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("product",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "updated_at")
    list_filter = ("status", "updated_at")
    search_fields = ("user__email",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (CartItemInline,)


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ("country_code", "name", "amount_cad", "estimated_days_min", "estimated_days_max", "is_active")
    list_editable = ("amount_cad", "is_active")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "sku", "name", "quantity", "unit_price_cad", "line_total_cad")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "customer_email", "status", "total_cad", "paid_at")
    list_filter = ("status", "paid_at")
    search_fields = ("number", "customer_email", "paypal_order_id", "paypal_capture_id")
    readonly_fields = (
        "id", "number", "user", "checkout_session", "currency", "customer_email",
        "shipping_address", "subtotal_cad", "shipping_cad", "tax_cad", "total_cad",
        "paypal_order_id", "paypal_capture_id", "paid_at", "created_at", "updated_at",
    )
    inlines = (OrderItemInline,)


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total_cad", "paypal_order_id", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "paypal_order_id")
    readonly_fields = [field.name for field in CheckoutSession._meta.fields]


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("external_id", "event_type", "status", "received_at", "processed_at")
    list_filter = ("status", "event_type", "received_at")
    search_fields = ("external_id", "event_type")
    readonly_fields = [field.name for field in PaymentWebhookEvent._meta.fields]


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("source_name", "status", "created_count", "updated_count", "error_count", "started_at")
    list_filter = ("status", "started_at")
    readonly_fields = [field.name for field in ImportJob._meta.fields]

