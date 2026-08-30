from django.db import models

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
    def in_stock(self): return not self.track_inventory or self.inventory_quantity > 0
    def __str__(self): return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt_text = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
