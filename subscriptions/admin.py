from django.contrib import admin

from .models import PaymentEvent, Subscription, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("email", "telegram_id", "created_at")
    search_fields = ("email", "telegram_id")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan_name", "status", "expires_at", "auto_renew")
    list_filter = ("status", "auto_renew", "plan_name")
    search_fields = ("user__email",)


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "user", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("event_id", "user__email")
    readonly_fields = ("raw_payload",)
