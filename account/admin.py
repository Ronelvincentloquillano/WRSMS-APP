from django.contrib import admin
from .models import SubscriptionPlan, StationSubscription, PendingRegistration

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'transaction_limit')

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