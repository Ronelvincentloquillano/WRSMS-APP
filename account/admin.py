from django.contrib import admin
from .models import SubscriptionPlan, StationSubscription, PendingRegistration, SubscriptionPaymentRequest

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_monthly', 'price_annual', 'transaction_limit')

@admin.register(StationSubscription)
class StationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('station', 'plan', 'start_date', 'end_date', 'is_trial', 'is_active', 'is_valid_status')
    list_filter = ('is_trial', 'is_active', 'plan', 'end_date')
    search_fields = ('station__name',)
    autocomplete_fields = ['station']

    def is_valid_status(self, obj):
        return obj.is_valid
    is_valid_status.boolean = True
    is_valid_status.short_description = 'Valid'

@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ('email', 'station_name', 'plan_name', 'created_at')
    search_fields = ('email', 'station_name')


@admin.register(SubscriptionPaymentRequest)
class SubscriptionPaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('station', 'plan', 'billing_cycle', 'amount', 'reference_number', 'status', 'created_at')
    list_filter = ('status', 'billing_cycle', 'plan')
    search_fields = ('station__name', 'reference_number', 'payer_name', 'payer_number')