from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wrsm_app', '0049_create_station_user_roles'),
        ('account', '0005_force_annual_prices'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPaymentRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('billing_cycle', models.CharField(choices=[('monthly', 'Monthly'), ('annual', 'Annual')], default='monthly', max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reference_number', models.CharField(max_length=100)),
                ('payer_name', models.CharField(blank=True, max_length=100)),
                ('payer_number', models.CharField(blank=True, max_length=20)),
                ('proof_image', models.ImageField(upload_to='subscription_proofs/')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('admin_note', models.CharField(blank=True, max_length=200)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_subscription_payment_requests', to=settings.AUTH_USER_MODEL)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscription_payment_requests', to='account.subscriptionplan')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_subscription_payment_requests', to=settings.AUTH_USER_MODEL)),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscription_payment_requests', to='wrsm_app.station')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
