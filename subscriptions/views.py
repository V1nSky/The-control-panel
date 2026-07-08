import json
import logging

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from .models import Subscription, UserProfile
from .services import extend_subscription, process_webhook_event

logger = logging.getLogger("subscriptions.webhook")


@csrf_exempt
@require_POST
def payment_webhook(request):
    """POST /api/payment-webhook/

    Accepts a mock payment-provider payload:
    {"event_id": "...", "email": "...", "amount": 1000, "status": "success"}
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid JSON body"}, status=400)

    required_fields = ("event_id", "email", "amount", "status")
    missing = [f for f in required_fields if f not in payload]
    if missing:
        return JsonResponse(
            {"ok": False, "error": f"missing fields: {', '.join(missing)}"},
            status=400,
        )

    payment_event, created = process_webhook_event(payload)

    if not created:
        return JsonResponse(
            {"ok": True, "duplicate": True, "event_id": payment_event.event_id},
            status=200,
        )

    return JsonResponse(
        {
            "ok": True,
            "duplicate": False,
            "event_id": payment_event.event_id,
            "status": payment_event.status,
        },
        status=201,
    )


@require_http_methods(["GET"])
def dashboard(request):
    """GET /dashboard/?email=...

    Simple read-only dashboard. No auth per the assignment spec — pass
    ?email= to view a specific user, otherwise the first available profile
    is shown (demo convenience).
    """
    email = request.GET.get("email")
    if email:
        user = UserProfile.objects.filter(email=email).first()
    else:
        user = UserProfile.objects.order_by("created_at").first()

    subscription = getattr(user, "subscription", None) if user else None

    context = {
        "user": user,
        "subscription": subscription,
    }
    return render(request, "subscriptions/dashboard.html", context)


@require_POST
def mock_renew(request):
    """POST /dashboard/renew/

    Mock-only manual "Продлить подписку" button. Extends the subscription
    by 30 days without touching any real payment provider.
    """
    email = request.POST.get("email")
    user = UserProfile.objects.filter(email=email).first()
    if user and hasattr(user, "subscription"):
        extend_subscription(user.subscription)
        logger.info("Manual mock renewal triggered for %s", email)

    redirect_url = "/dashboard/"
    if email:
        redirect_url += f"?email={email}"
    return redirect(redirect_url)
