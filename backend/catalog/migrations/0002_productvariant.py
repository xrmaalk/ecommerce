import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(max_length=80, unique=True)),
                ("size", models.CharField(blank=True, max_length=60)),
                ("color", models.CharField(blank=True, max_length=60)),
                ("label", models.CharField(blank=True, max_length=100, help_text="Optional other variation, such as scent, flavor, or material.")),
                ("price_cad", models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2, validators=[django.core.validators.MinValueValidator(0)], help_text="Leave blank to use the product price.")),
                ("inventory_quantity", models.PositiveIntegerField(default=0)),
                ("track_inventory", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="catalog.product")),
            ],
            options={"ordering": ("sort_order", "id"), "constraints": [models.UniqueConstraint(fields=("product", "size", "color", "label"), name="unique_product_variant_options")]},
        ),
    ]
