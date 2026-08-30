import base64
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


class AvaTaxAdapter:
    """Calculate checkout tax with Avalara AvaTax.

    Quotes are created as uncommitted SalesOrder transactions. Recording the
    final paid sale for filing is intentionally a separate concern from
    checkout calculation.
    """

    timeout = 20

    def __init__(self):
        self.account_id = settings.AVATAX_ACCOUNT_ID
        self.license_key = settings.AVATAX_LICENSE_KEY
        self.company_code = settings.AVATAX_COMPANY_CODE
        self.environment = settings.AVATAX_ENVIRONMENT
        self.base_url = (
            "https://rest.avatax.com"
            if self.environment == "production"
            else "https://sandbox-rest.avatax.com"
        )

    def _configuration(self):
        values = {
            "AVATAX_ACCOUNT_ID": self.account_id,
            "AVATAX_LICENSE_KEY": self.license_key,
            "AVATAX_COMPANY_CODE": self.company_code,
            "AVATAX_ORIGIN_LINE1": settings.AVATAX_ORIGIN_LINE1,
            "AVATAX_ORIGIN_CITY": settings.AVATAX_ORIGIN_CITY,
            "AVATAX_ORIGIN_REGION": settings.AVATAX_ORIGIN_REGION,
            "AVATAX_ORIGIN_POSTAL_CODE": settings.AVATAX_ORIGIN_POSTAL_CODE,
            "AVATAX_ORIGIN_COUNTRY": settings.AVATAX_ORIGIN_COUNTRY,
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise TaxUnavailable(
                "Automated tax calculation is not fully configured."
            )
        return values

    @staticmethod
    def _money(value):
        return f"{Decimal(value):.2f}"

    @staticmethod
    def _destination(address):
        destination = {
            "line1": address["address_line_1"],
            "city": address["city"],
            "region": address["region"],
            "postalCode": address["postal_code"],
            "country": address["country_code"],
        }
        if address.get("address_line_2"):
            destination["line2"] = address["address_line_2"]
        return destination

    def _payload(self, *, shipping, address, items):
        config = self._configuration()
        lines = [
            {
                "number": str(index),
                "quantity": item["quantity"],
                "amount": self._money(item["line_total_cad"]),
                "itemCode": item["sku"],
                "description": item["name"],
            }
            for index, item in enumerate(items, start=1)
        ]
        if Decimal(shipping) > 0:
            lines.append({
                "number": str(len(lines) + 1),
                "quantity": 1,
                "amount": self._money(shipping),
                "itemCode": "SHIPPING",
                "description": "Standard shipping",
                "taxCode": "FR020100",
            })
        return {
            "type": "SalesOrder",
            "companyCode": self.company_code,
            "date": date.today().isoformat(),
            "customerCode": "ORGANIC-EMPEROR-CUSTOMER",
            "currencyCode": "CAD",
            "commit": False,
            "addresses": {
                "shipFrom": {
                    "line1": config["AVATAX_ORIGIN_LINE1"],
                    "city": config["AVATAX_ORIGIN_CITY"],
                    "region": config["AVATAX_ORIGIN_REGION"],
                    "postalCode": config["AVATAX_ORIGIN_POSTAL_CODE"],
                    "country": config["AVATAX_ORIGIN_COUNTRY"],
                },
                "shipTo": self._destination(address),
            },
            "lines": lines,
        }

    def calculate(self, *, subtotal, shipping, address, items):
        del subtotal  # AvaTax derives the taxable amount from authoritative lines.
        payload = self._payload(shipping=shipping, address=address, items=items)
        credentials = base64.b64encode(
            f"{self.account_id}:{self.license_key}".encode()
        ).decode()
        request = Request(
            f"{self.base_url}/api/v2/transactions/create",
            data=json.dumps(payload).encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
                "X-Avalara-Client": "OrganicEmperor-Django;1.5.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode())
        except HTTPError as error:
            error.read()
            raise TaxUnavailable(
                f"Automated tax calculation was rejected (HTTP {error.code})."
            ) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise TaxUnavailable(
                "Automated tax calculation is temporarily unavailable."
            ) from error

        if not isinstance(result, dict):
            raise TaxUnavailable("The tax provider returned an incomplete quote.")
        total_tax = result.get("totalTax")
        if total_tax is None:
            raise TaxUnavailable("The tax provider returned an incomplete quote.")
        try:
            amount = Decimal(str(total_tax))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise TaxUnavailable("The tax provider returned an invalid quote.") from error
        if amount < 0:
            raise TaxUnavailable("The tax provider returned an invalid quote.")
        reference = str(result.get("code") or result.get("id") or "")
        return TaxQuote(amount=amount, provider="avalara-avatax", reference=reference)


def get_tax_adapter():
    adapter_class = import_string(settings.COMMERCE_TAX_ADAPTER)
    return adapter_class()
