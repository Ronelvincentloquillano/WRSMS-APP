from decimal import Decimal

from django.db import migrations


ANNUAL_PRICES = {
    "Sediment": Decimal("1788.00"),
    "Carbon": Decimal("2388.00"),
    "RO": Decimal("2988.00"),
}


def forwards(apps, schema_editor):
    SubscriptionPlan = apps.get_model("account", "SubscriptionPlan")
    for plan in SubscriptionPlan.objects.all():
        annual = ANNUAL_PRICES.get(plan.name)
        if annual is None:
            # Fallback for any extra/custom plans.
            annual = (plan.price_monthly or Decimal("0.00")) * Decimal("12")
        plan.price_annual = annual
        plan.save(update_fields=["price_annual"])


def backwards(apps, schema_editor):
    SubscriptionPlan = apps.get_model("account", "SubscriptionPlan")
    SubscriptionPlan.objects.all().update(price_annual=Decimal("0.00"))


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0003_subscription_plan_prices_and_limits"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

