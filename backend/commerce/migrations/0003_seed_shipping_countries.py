from decimal import Decimal

from django.db import migrations


def seed_shipping_countries(apps, schema_editor):
    ShippingRate = apps.get_model("commerce", "ShippingRate")
    for country_code in ("CA", "US"):
        ShippingRate.objects.get_or_create(
            country_code=country_code,
            defaults={
                "name": "Standard shipping",
                "amount_cad": Decimal("0.00"),
                "estimated_days_min": 3,
                "estimated_days_max": 10,
                "is_active": False,
            },
        )


def remove_seeded_shipping_countries(apps, schema_editor):
    ShippingRate = apps.get_model("commerce", "ShippingRate")
    ShippingRate.objects.filter(
        country_code__in=("CA", "US"),
        amount_cad=Decimal("0.00"),
        is_active=False,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("commerce", "0002_checkoutsession_expires_at")]

    operations = [
        migrations.RunPython(seed_shipping_countries, remove_seeded_shipping_countries),
    ]
