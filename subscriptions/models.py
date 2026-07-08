from django.db import models


class UserProfile(models.Model):
    """A VPN service user."""
    email = models.EmailField(unique=True)
    telegram_id = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class Subscription(models.Model):
    """A user's VPN subscription plan/state."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        PENDING = "pending", "Pending"

    user = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, related_name="subscription"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    plan_name = models.CharField(max_length=64, default="Basic")
    expires_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} — {self.plan_name} ({self.status})"


class PaymentEvent(models.Model):
    """A raw payment/webhook event received from the (mock) payment provider."""

    event_id = models.CharField(max_length=128, unique=True)
    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="payment_events",
        null=True, blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=32)
    raw_payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_id} ({self.status})"
