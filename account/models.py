from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from wrsm_app.models import Station

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    transaction_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Null for unlimited")
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_annual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class StationSubscription(models.Model):
    station = models.OneToOneField(Station, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_trial = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.station.name} - {self.plan.name if self.plan else 'No Plan'}"

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.end_date and self.end_date < timezone.now().date():
            return False
        return True

class PendingRegistration(models.Model):
    email = models.EmailField(unique=True)
    station_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=128) # Store hashed? Or temporary?
    plan_name = models.CharField(max_length=50, default='Trial')
    activation_key = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class SubscriptionPaymentRequest(models.Model):
    BILLING_CYCLE_CHOICES = (
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='subscription_payment_requests')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='subscription_payment_requests')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='monthly')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=100)
    payer_name = models.CharField(max_length=100, blank=True)
    payer_number = models.CharField(max_length=20, blank=True)
    proof_image = models.ImageField(upload_to='subscription_proofs/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_note = models.CharField(max_length=200, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_subscription_payment_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_subscription_payment_requests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.station} - {self.plan} - {self.status}"
