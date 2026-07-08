from django.core.management.base import BaseCommand

from subscriptions.services import run_auto_renew_check


class Command(BaseCommand):
    help = (
        "Mock auto-renewal sweep. Renews (by 30 days) any subscription with "
        "auto_renew=True that has expired. Subscriptions with auto_renew=False "
        "are left untouched. No real payment is triggered."
    )

    def handle(self, *args, **options):
        renewed = run_auto_renew_check()
        if not renewed:
            self.stdout.write("No subscriptions needed renewal.")
            return
        for sub in renewed:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Renewed {sub.user.email} -> new expiry {sub.expires_at}"
                )
            )
