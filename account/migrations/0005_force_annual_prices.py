from decimal import Decimal

from django.db import migrations


def forwards(apps, schema_editor):
    SubscriptionPlan = apps.get_model("account", "SubscriptionPlan")

    # Force canonical annual prices for known plans.
    SubscriptionPlan.objects.filter(name="Sediment").update(price_annual=Decimal("1788.00"))
    SubscriptionPlan.objects.filter(name="Carbon").update(price_annual=Decimal("2388.00"))
    SubscriptionPlan.objects.filter(name="RO").update(price_annual=Decimal("2988.00"))

    # Fallback for any custom plans that still have zero annual.
    for plan in SubscriptionPlan.objects.filter(price_annual=Decimal("0.00")):
        monthly = plan.price_monthly or Decimal("0.00")
        plan.price_annual = monthly * Decimal("12")
        plan.save(update_fields=["price_annual"])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0004_set_subscription_plan_annual_prices"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

