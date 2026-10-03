import base64
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
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
        self.account_id = settings.AVATAX_ACCOUNT_ID.strip()
        self.license_key = settings.AVATAX_LICENSE_KEY.strip()
        self.company_code = settings.AVATAX_COMPANY_CODE.strip()
        self.environment = settings.AVATAX_ENVIRONMENT.strip().lower()
        self.base_url = (
            "https://rest.avatax.com"
            if self.environment == "production"
            else "https://sandbox-rest.avatax.com"
        )

    def _configuration_values(self):
        return {name: value.strip() for name, value in {
            "AVATAX_ACCOUNT_ID": self.account_id,
            "AVATAX_LICENSE_KEY": self.license_key,
            "AVATAX_COMPANY_CODE": self.company_code,
            "AVATAX_ORIGIN_LINE1": settings.AVATAX_ORIGIN_LINE1,
            "AVATAX_ORIGIN_CITY": settings.AVATAX_ORIGIN_CITY,
            "AVATAX_ORIGIN_REGION": settings.AVATAX_ORIGIN_REGION,
            "AVATAX_ORIGIN_POSTAL_CODE": settings.AVATAX_ORIGIN_POSTAL_CODE,
            "AVATAX_ORIGIN_COUNTRY": settings.AVATAX_ORIGIN_COUNTRY,
        }.items()}

    def configuration_issues(self):
        """Return setup problems by setting name, without including any values."""
        values = self._configuration_values()
        issues = []
        if self.environment not in ("sandbox", "production"):
            issues.append("AVATAX_ENVIRONMENT must be sandbox or production.")
        for name, value in values.items():
            if not value:
                issues.append(f"{name} is missing.")
            elif value.lower().startswith("your-"):
                issues.append(f"{name} still contains an example value.")
        if self.account_id and not (
            self.account_id.isascii() and self.account_id.isdigit()
            and int(self.account_id) > 0
        ):
            issues.append("AVATAX_ACCOUNT_ID must be the numeric AvaTax account ID.")
        if any(character.isspace() for character in self.license_key):
            issues.append("AVATAX_LICENSE_KEY must not contain whitespace.")
        return issues

    def _configuration(self):
        if self.configuration_issues():
            raise TaxUnavailable(
                "Automated tax calculation is not fully configured."
            )
        return self._configuration_values()

    def _request_json(self, path, *, payload=None):
        credentials = base64.b64encode(
            f"{self.account_id}:{self.license_key}".encode()
        ).decode()
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
                "X-Avalara-Client": "OrganicEmperor-Django;1.5.0",
            },
            method="POST" if payload is not None else "GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode())
        except HTTPError as error:
            # Provider bodies can contain account or address information.
            error.close()
            raise TaxUnavailable(
                f"Automated tax calculation was rejected (HTTP {error.code})."
            ) from None
        except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
            raise TaxUnavailable(
                "Automated tax calculation is temporarily unavailable."
            ) from None
        if not isinstance(result, dict):
            raise TaxUnavailable("The tax provider returned an incomplete response.")
        return result

    def check_connection(self):
        """Read authentication and company status; never create transactions."""
        self._configuration()
        ping = self._request_json("/api/v2/utilities/ping")
        if ping.get("authenticated") is not True:
            raise TaxUnavailable(
                "AvaTax authentication failed. Check the account ID and license key "
                "belong to the selected AVATAX_ENVIRONMENT."
            )
        company_code = self.company_code.replace("'", "''")
        query = urlencode({"$filter": f"companyCode eq '{company_code}'", "$top": 2})
        result = self._request_json(f"/api/v2/companies?{query}")
        companies = result.get("value")
        if not isinstance(companies, list) or not all(isinstance(company, dict) for company in companies):
            raise TaxUnavailable("AvaTax returned an incomplete company response.")
        matches = [company for company in companies if company.get("companyCode") == self.company_code]
        if len(matches) != 1:
            raise TaxUnavailable(
                "AVATAX_COMPANY_CODE does not identify an accessible company in this account."
            )
        if matches[0].get("isActive") is not True:
            raise TaxUnavailable("The AvaTax company must be activated before checkout can calculate tax.")

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
        result = self._request_json("/api/v2/transactions/create", payload=payload)
        total_tax = result.get("totalTax")
        if total_tax is None:
            raise TaxUnavailable("The tax provider returned an incomplete quote.")
        try:
            amount = Decimal(str(total_tax))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise TaxUnavailable("The tax provider returned an invalid quote.") from error
        if not amount.is_finite() or amount < 0:
            raise TaxUnavailable("The tax provider returned an invalid quote.")
        reference = str(result.get("code") or result.get("id") or "")
        return TaxQuote(amount=amount, provider="avalara-avatax", reference=reference)


def get_tax_adapter():
    adapter_class = import_string(settings.COMMERCE_TAX_ADAPTER)
    return adapter_class()
