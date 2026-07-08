from django.urls import path

from . import views

urlpatterns = [
    path("api/payment-webhook/", views.payment_webhook, name="payment-webhook"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/renew/", views.mock_renew, name="mock-renew"),
]
