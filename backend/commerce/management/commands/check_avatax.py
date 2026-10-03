from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from commerce.tax import AvaTaxAdapter, TaxUnavailable


class Command(BaseCommand):
    help = "Check AvaTax setup and optionally verify credentials/company with read-only API requests."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--local-only", action="store_true",
            help="Validate loaded settings without contacting AvaTax.",
        )

    def handle(self, *args, **options):
        if settings.COMMERCE_TAX_ADAPTER != "commerce.tax.AvaTaxAdapter":
            raise CommandError("Set COMMERCE_TAX_ADAPTER=commerce.tax.AvaTaxAdapter first.")
        adapter = AvaTaxAdapter()
        issues = adapter.configuration_issues()
        if settings.COMMERCE_ALLOW_ZERO_TAX:
            issues.append("Set COMMERCE_ALLOW_ZERO_TAX=False for AvaTax checkout.")
        if issues:
            raise CommandError("AvaTax setup is incomplete:\n" + "\n".join(f"- {issue}" for issue in issues))
        self.stdout.write(f"AvaTax environment: {adapter.environment}; endpoint: {adapter.base_url}")
        if options["local_only"]:
            self.stdout.write("Local settings passed. Authentication and company status have not been verified.")
            return
        try:
            adapter.check_connection()
        except TaxUnavailable as error:
            raise CommandError(
                f"AvaTax connection check failed: {error}\n"
                "For HTTP 401, check matching environment/account/license key. "
                "Do not share credentials or reset an existing key just to retry."
            ) from None
        self.stdout.write(self.style.SUCCESS(
            "AvaTax authentication and active company verified. No tax transactions were created. "
            "Verify company tax settings and a checkout quote separately."
        ))
