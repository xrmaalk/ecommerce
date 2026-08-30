from decimal import Decimal

from rest_framework import serializers

from catalog.models import Product
from catalog.serializers import ProductSerializer

from .models import Cart, CheckoutSession, Order, OrderItem, ShippingRate


class CartItemSerializer(serializers.Serializer):
    product = ProductSerializer(read_only=True)
    quantity = serializers.IntegerField(min_value=1, max_value=99)
    unit_price_cad = serializers.SerializerMethodField()
    line_total_cad = serializers.SerializerMethodField()

    def get_unit_price_cad(self, obj):
        return f"{obj.product.price_cad:.2f}"

    def get_line_total_cad(self, obj):
        return f"{obj.product.price_cad * obj.quantity:.2f}"


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    subtotal_cad = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "currency", "items", "item_count", "subtotal_cad", "updated_at")

    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_subtotal_cad(self, obj):
        total = sum((item.product.price_cad * item.quantity for item in obj.items.all()), Decimal("0.00"))
        return f"{total:.2f}"


class CartItemWriteSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source="product", queryset=Product.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=0, max_value=99)


class CartMergeItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=99)


class CartMergeSerializer(serializers.Serializer):
    items = CartMergeItemSerializer(many=True, allow_empty=True)

    def validate_items(self, value):
        ids = [item["product_id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each product may appear only once.")
        return value


class ShippingRateSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source="get_country_code_display", read_only=True)

    class Meta:
        model = ShippingRate
        fields = (
            "country_code", "country", "name", "amount_cad",
            "estimated_days_min", "estimated_days_max",
        )


class ShippingAddressSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    address_line_1 = serializers.CharField(max_length=180)
    address_line_2 = serializers.CharField(max_length=180, required=False, allow_blank=True, default="")
    city = serializers.CharField(max_length=120)
    region = serializers.CharField(max_length=80)
    postal_code = serializers.CharField(max_length=20)
    country_code = serializers.ChoiceField(choices=("CA", "US"))
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        return {
            key: value.strip() if isinstance(value, str) else value
            for key, value in attrs.items()
        }


class CheckoutSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckoutSession
        fields = (
            "id", "status", "currency", "shipping_address", "line_items",
            "subtotal_cad", "shipping_cad", "tax_cad", "total_cad",
            "tax_provider", "paypal_order_id", "created_at",
        )
        read_only_fields = fields


class CheckoutCreateOrderSerializer(serializers.Serializer):
    checkout_session_id = serializers.PrimaryKeyRelatedField(
        source="checkout_session", queryset=CheckoutSession.objects.none()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context["request"]
        self.fields["checkout_session_id"].queryset = CheckoutSession.objects.filter(
            user=request.user,
            status__in=(CheckoutSession.Status.OPEN, CheckoutSession.Status.PAYPAL_CREATED),
        )


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("sku", "name", "quantity", "unit_price_cad", "line_total_cad")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "number", "status", "currency", "customer_email", "shipping_address",
            "subtotal_cad", "shipping_cad", "tax_cad", "total_cad", "items",
            "paid_at", "created_at",
        )

