# Data migration: align public pricing with SubscriptionPlan rows (monthly price + transaction tier).

from decimal import Decimal

from django.db import migrations


PLANS = (
    (
        'Sediment',
        Decimal('149.00'),
        300,
        'Core operations: sales, customers, products, containers, and dashboard. Best for smaller stations.',
    ),
    (
        'Carbon',
        Decimal('199.00'),
        500,
        'Adds finance and growth tools: AR, net terms, expenses, forecasts, delivery map, promos, and discounts.',
    ),
    (
        'RO',
        Decimal('249.00'),
        None,
        'Full platform: everything in Carbon plus audit logs, shortcuts, backwash monitor, and unlimited monthly transactions.',
    ),
)


def forwards(apps, schema_editor):
    SubscriptionPlan = apps.get_model('account', 'SubscriptionPlan')
    for name, price_monthly, transaction_limit, description in PLANS:
        obj, created = SubscriptionPlan.objects.get_or_create(
            name=name,
            defaults={
                'price_monthly': price_monthly,
                'price_annual': Decimal('0.00'),
                'transaction_limit': transaction_limit,
                'description': description,
            },
        )
        if not created:
            obj.price_monthly = price_monthly
            if not obj.price_annual:
                obj.price_annual = Decimal('0.00')
            obj.transaction_limit = transaction_limit
            obj.description = description
            obj.save(update_fields=['price_monthly', 'price_annual', 'transaction_limit', 'description'])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_remove_subscriptionplan_price_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
