from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductVariant

class ProductVariantSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    price_cad = serializers.DecimalField(source="effective_price_cad", max_digits=10, decimal_places=2, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ("id", "sku", "size", "color", "label", "name", "price_cad", "inventory_quantity", "track_inventory", "in_stock")

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "sort_order")

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description")

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    variants = serializers.SerializerMethodField()
    has_variants = serializers.SerializerMethodField()

    def get_variants(self, obj):
        return ProductVariantSerializer([variant for variant in obj.variants.all() if variant.is_active], many=True).data

    def get_has_variants(self, obj):
        return bool(list(obj.variants.all()))

    class Meta:
        model = Product
        fields = ("id", "name", "slug", "sku", "category", "short_description", "description", "price_cad", "compare_at_price_cad", "inventory_quantity", "track_inventory", "in_stock", "is_featured", "images", "updated_at", "has_variants", "variants")
