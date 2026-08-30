from decimal import Decimal

from django.db import migrations


INITIAL_RATES = {
    "CA": Decimal("15.00"),
    "US": Decimal("25.00"),
}


def configure_initial_shipping_rates(apps, schema_editor):
    ShippingRate = apps.get_model("commerce", "ShippingRate")
    for country_code, amount_cad in INITIAL_RATES.items():
        ShippingRate.objects.update_or_create(
            country_code=country_code,
            defaults={
                "name": "Standard shipping",
                "amount_cad": amount_cad,
                "estimated_days_min": 3,
                "estimated_days_max": 10,
                "is_active": True,
            },
        )


def restore_unconfigured_shipping_rates(apps, schema_editor):
    ShippingRate = apps.get_model("commerce", "ShippingRate")
    for country_code, amount_cad in INITIAL_RATES.items():
        ShippingRate.objects.filter(
            country_code=country_code,
            name="Standard shipping",
            amount_cad=amount_cad,
            estimated_days_min=3,
            estimated_days_max=10,
            is_active=True,
        ).update(amount_cad=Decimal("0.00"), is_active=False)


class Migration(migrations.Migration):
    dependencies = [("commerce", "0004_checkoutsession_inventory_reserved_at")]

    operations = [
        migrations.RunPython(
            configure_initial_shipping_rates,
            restore_unconfigured_shipping_rates,
        ),
    ]
