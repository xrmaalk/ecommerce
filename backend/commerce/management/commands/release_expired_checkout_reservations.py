from django.core.management.base import BaseCommand
from django.utils import timezone

from commerce.models import CheckoutSession
from commerce.services import release_inventory_reservation


class Command(BaseCommand):
    help = "Release inventory held by expired, incomplete PayPal checkout sessions."

    def handle(self, *args, **options):
        session_ids = list(
            CheckoutSession.objects.filter(
                inventory_reserved_at__isnull=False,
                expires_at__lte=timezone.now(),
                status__in=(CheckoutSession.Status.OPEN, CheckoutSession.Status.PAYPAL_CREATED),
            ).values_list("id", flat=True)
        )
        for session_id in session_ids:
            release_inventory_reservation(session_id)
        self.stdout.write(self.style.SUCCESS(f"Released {len(session_ids)} expired reservation(s)."))
