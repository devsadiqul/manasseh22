from datetime import timedelta
from django.utils import timezone
from .models import Subscription

PLAN_PRICING = {
    "monthly": {"amount": 9.99, "duration_days": 30},
    "yearly":  {"amount": 99.99, "duration_days": 365},
}


def create_default_subscription(user):
    Subscription.objects.get_or_create(user=user, defaults={"plan": "free"})


def activate_premium_subscription(user, billing_cycle):
    pricing = PLAN_PRICING.get(billing_cycle)
    if not pricing:
        raise ValueError("Invalid billing cycle.")
    subscription, _ = Subscription.objects.get_or_create(user=user)
    now = timezone.now()
    base = subscription.valid_until if subscription.valid_until and subscription.valid_until > now else now
    subscription.plan = "premium"
    subscription.billing_cycle = billing_cycle
    subscription.valid_until = base + timedelta(days=pricing["duration_days"])
    subscription.is_active = True
    subscription.save()
    return subscription