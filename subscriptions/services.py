import logging
from datetime import timedelta

from django.utils import timezone

from .models import PaymentEvent, Subscription, UserProfile

logger = logging.getLogger("subscriptions.webhook")

RENEWAL_DAYS = 30


def extend_subscription(subscription: Subscription, days: int = RENEWAL_DAYS) -> Subscription:
    """Push expires_at forward by `days`, starting from whichever is later:
    the current expiry (if still in the future) or now. Marks the
    subscription active and saves it."""
    now = timezone.now()
    base = subscription.expires_at if subscription.expires_at and subscription.expires_at > now else now
    subscription.expires_at = base + timedelta(days=days)
    subscription.status = Subscription.Status.ACTIVE
    subscription.save()
    return subscription


def process_webhook_event(payload: dict) -> tuple[PaymentEvent, bool]:
    """Process a mock payment-provider webhook payload.

    Returns (payment_event, created) where `created` is False if this
    event_id had already been processed before (idempotent dedup).
    """
    event_id = payload.get("event_id")
    email = payload.get("email")
    amount = payload.get("amount")
    status = payload.get("status")

    existing = PaymentEvent.objects.filter(event_id=event_id).first()
    if existing:
        logger.info("Duplicate webhook event ignored: %s", event_id)
        return existing, False

    user, _ = UserProfile.objects.get_or_create(email=email)

    payment_event = PaymentEvent.objects.create(
        event_id=event_id,
        user=user,
        amount=amount,
        status=status,
        raw_payload=payload,
    )
    logger.info("New webhook event stored: %s (status=%s)", event_id, status)

    if status == "success":
        subscription, _ = Subscription.objects.get_or_create(user=user)
        extend_subscription(subscription)
        logger.info(
            "Subscription for %s activated, extended to %s",
            user.email, subscription.expires_at,
        )

    return payment_event, True


def run_auto_renew_check():
    """Mock auto-renewal sweep: any subscription with auto_renew=True whose
    expires_at has passed (or is missing) gets renewed for another 30 days.
    Subscriptions with auto_renew=False are left untouched, even if expired.
    No real payment is triggered — this only simulates the provider callback.
    """
    now = timezone.now()
    renewed = []
    candidates = Subscription.objects.filter(auto_renew=True).filter(
        models_q_expired(now)
    )
    for sub in candidates:
        extend_subscription(sub)
        renewed.append(sub)
        logger.info("Auto-renewed subscription for %s", sub.user.email)
    return renewed


def models_q_expired(now):
    from django.db.models import Q
    return Q(expires_at__lte=now) | Q(expires_at__isnull=True)
