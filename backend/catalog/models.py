from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "categories"

    def __str__(self): return self.name

class Product(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    sku = models.CharField(max_length=80, unique=True)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)
    short_description = models.CharField(max_length=280, blank=True)
    description = models.TextField(blank=True)
    price_cad = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price_cad = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    inventory_quantity = models.PositiveIntegerField(default=0)
    track_inventory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_featured", "name")

    @property
    def in_stock(self):
        variants = list(self.variants.all())
        if variants:
            return any(variant.is_active and variant.in_stock for variant in variants)
        return not self.track_inventory or self.inventory_quantity > 0
    def __str__(self): return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt_text = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    sku = models.CharField(max_length=80, unique=True)
    size = models.CharField(max_length=60, blank=True)
    color = models.CharField(max_length=60, blank=True)
    label = models.CharField(max_length=100, blank=True, help_text="Optional other variation, such as scent, flavor, or material.")
    price_cad = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=(MinValueValidator(0),), help_text="Leave blank to use the product price.")
    inventory_quantity = models.PositiveIntegerField(default=0)
    track_inventory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
        constraints = [models.UniqueConstraint(fields=("product", "size", "color", "label"), name="unique_product_variant_options")]

    @property
    def name(self):
        return " / ".join(filter(None, (f"Size: {self.size}" if self.size else "", f"Color: {self.color}" if self.color else "", self.label)))

    @property
    def effective_price_cad(self):
        return self.price_cad if self.price_cad is not None else self.product.price_cad

    @property
    def in_stock(self):
        return not self.track_inventory or self.inventory_quantity > 0

    def clean(self):
        super().clean()
        self.size, self.color, self.label = self.size.strip(), self.color.strip(), self.label.strip()
        if not any((self.size, self.color, self.label)):
            raise ValidationError("Enter a size, color, or other variation label.")
        if Product.objects.filter(sku=self.sku).exists():
            raise ValidationError({"sku": "Use a SKU different from the base product SKU."})

    def __str__(self):
        return f"{self.product} — {self.name}"
