import json

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import PaymentEvent, Subscription, UserProfile
from .services import run_auto_renew_check


class PaymentWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("payment-webhook")

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_success_event_activates_subscription(self):
        payload = {
            "event_id": "evt_123",
            "email": "user@test.com",
            "amount": 1000,
            "status": "success",
        }
        response = self._post(payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PaymentEvent.objects.count(), 1)

        user = UserProfile.objects.get(email="user@test.com")
        self.assertEqual(user.subscription.status, Subscription.Status.ACTIVE)
        self.assertIsNotNone(user.subscription.expires_at)
        # roughly 30 days from now
        self.assertGreater(
            user.subscription.expires_at, timezone.now() + timedelta(days=29)
        )

    def test_duplicate_event_id_is_ignored(self):
        payload = {
            "event_id": "evt_dup",
            "email": "dup@test.com",
            "amount": 500,
            "status": "success",
        }
        first = self._post(payload)
        second = self._post(payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual(PaymentEvent.objects.count(), 1)

    def test_missing_fields_returns_400(self):
        response = self._post({"event_id": "evt_bad"})
        self.assertEqual(response.status_code, 400)

    def test_non_success_status_does_not_activate(self):
        payload = {
            "event_id": "evt_fail",
            "email": "fail@test.com",
            "amount": 100,
            "status": "failed",
        }
        self._post(payload)
        user = UserProfile.objects.get(email="fail@test.com")
        # No subscription should have been created for a failed payment.
        self.assertFalse(hasattr(user, "subscription"))


class AutoRenewTests(TestCase):
    def test_auto_renew_only_touches_enabled_subscriptions(self):
        expired_time = timezone.now() - timedelta(days=1)

        renew_user = UserProfile.objects.create(email="renew@test.com")
        renew_sub = Subscription.objects.create(
            user=renew_user, status=Subscription.Status.EXPIRED,
            expires_at=expired_time, auto_renew=True,
        )

        no_renew_user = UserProfile.objects.create(email="norenew@test.com")
        no_renew_sub = Subscription.objects.create(
            user=no_renew_user, status=Subscription.Status.EXPIRED,
            expires_at=expired_time, auto_renew=False,
        )

        renewed = run_auto_renew_check()

        renew_sub.refresh_from_db()
        no_renew_sub.refresh_from_db()

        self.assertIn(renew_sub, renewed)
        self.assertEqual(renew_sub.status, Subscription.Status.ACTIVE)
        self.assertGreater(renew_sub.expires_at, timezone.now())

        # untouched
        self.assertEqual(no_renew_sub.status, Subscription.Status.EXPIRED)
        self.assertEqual(no_renew_sub.expires_at, expired_time)
