from django.contrib import admin
from . import models

class StationRecordAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Allow superusers to see everything
        if request.user.is_superuser:
            return qs
        # Assume user's profile has `station` field
        return qs.filter(station=request.user.profile.station)


class ProductAdmin(StationRecordAdmin):
    list_display = ('product_name', 'station')

admin.site.register(models.Customer)
admin.site.register(models.CustomerGeneric)
admin.site.register(models.Sales)
admin.site.register(models.JugSize)
admin.site.register(models.OrderType)
admin.site.register(models.JugType)
admin.site.register(models.StationSetting)
class StationAdmin(admin.ModelAdmin):
    search_fields = ['name', 'station_code']
    list_display = ['name', 'station_code', 'contact_number']

admin.site.register(models.Station, StationAdmin)
admin.site.register(models.Promo)
admin.site.register(models.Discount)
admin.site.register(models.Profile)
admin.site.register(models.Maintenance)
admin.site.register(models.Expense)
admin.site.register(models.Forecast)
admin.site.register(models.SalesItem)
admin.site.register(models.Product, ProductAdmin)
admin.site.register(models.Order)
admin.site.register(models.PaymentType)
admin.site.register(models.ContainerInventory)
admin.site.register(models.AccountsReceivable)
admin.site.register(models.Payment)
admin.site.register(models.PaymentGeneric)
admin.site.register(models.PaymentItem)
admin.site.register(models.CustomerCredit)
admin.site.register(models.NetTerms)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_published', 'updated_at')
    search_fields = ('title', 'body')
    readonly_fields = ('date_published', 'updated_at')

admin.site.register(models.ShortCut)
admin.site.register(models.Article, ArticleAdmin)
