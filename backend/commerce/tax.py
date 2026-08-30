from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.utils.module_loading import import_string


class TaxUnavailable(Exception):
    pass


@dataclass(frozen=True)
class TaxQuote:
    amount: Decimal
    provider: str
    reference: str = ""


class UnavailableTaxAdapter:
    def calculate(self, *, subtotal, shipping, address, items):
        raise TaxUnavailable(
            "Automated tax calculation is not configured yet. Checkout remains safely disabled."
        )


class ZeroTaxAdapter:
    """Sandbox/test adapter. It cannot run unless explicitly enabled."""

    def calculate(self, *, subtotal, shipping, address, items):
        if not settings.COMMERCE_ALLOW_ZERO_TAX:
            raise TaxUnavailable("The zero-tax adapter is disabled.")
        return TaxQuote(amount=Decimal("0.00"), provider="zero-tax-sandbox")


def get_tax_adapter():
    adapter_class = import_string(settings.COMMERCE_TAX_ADAPTER)
    return adapter_class()

