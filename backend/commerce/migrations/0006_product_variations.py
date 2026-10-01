import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_productvariant"), ("commerce", "0005_configure_initial_shipping_rates")]
    operations = [
        migrations.AddField(model_name="cartitem", name="variant", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="cart_items", to="catalog.productvariant")),
        migrations.AddField(model_name="cartitem", name="variant_key", field=models.PositiveBigIntegerField(default=0, editable=False)),
        migrations.RemoveConstraint(model_name="cartitem", name="unique_product_per_cart"),
        migrations.AddConstraint(model_name="cartitem", constraint=models.UniqueConstraint(fields=("cart", "product", "variant_key"), name="unique_product_variation_per_cart")),
        migrations.AddField(model_name="orderitem", name="variation", field=models.CharField(blank=True, max_length=240)),
    ]
