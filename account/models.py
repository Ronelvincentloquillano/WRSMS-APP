from django.db import models
from django.utils import timezone
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
