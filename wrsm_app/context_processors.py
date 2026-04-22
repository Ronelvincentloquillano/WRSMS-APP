from .models import StationSetting
from .utils import is_transaction_limit_reached
from . import models
from django.core.exceptions import ObjectDoesNotExist

def global_context(request):
    has_station_settings = False
    settings_complete = False
    station = {'name':'Admin Water Refilling Station','id':0}
    limit_reached = False

    if not request.user.is_authenticated:
        return {
            'has_station_settings': has_station_settings,
            'settings_complete': settings_complete
        }

    try:
        profile = request.user.profile
    except ObjectDoesNotExist:
        profile = None

    if profile:
        station = profile.station
        limit_reached = is_transaction_limit_reached(station)
        setup_wizard_complete = (
            models.JugSize.objects.filter(station=station).exists()
            and models.JugType.objects.filter(station=station).exists()
            and models.OrderType.objects.filter(station=station).exists()
            and models.PaymentType.objects.filter(station=station).exists()
        )
        station_settings = StationSetting.objects.filter(station=station).order_by('-pk').first()
        if station_settings:
            has_station_settings = True
            required_fields = [
                station_settings.default_delivery_rate,
                station_settings.default_jug_size,
                station_settings.default_unit_price,
                station_settings.default_minimum_delivery_qty,
                station_settings.default_order_type,
                station_settings.default_payment_type,
            ]
            station_defaults_complete = all(field is not None for field in required_fields)
            # Sidebar/tabs visibility should follow setup wizard completion
            # while still honoring full station defaults when available.
            settings_complete = setup_wizard_complete or station_defaults_complete
        else:
            settings_complete = setup_wizard_complete
    
    available_stations = []
    if profile and profile.allowed_stations.count() > 1:
        available_stations = profile.allowed_stations.all()

    return {
        'station': station,
        'has_station_settings': has_station_settings,
        'settings_complete': settings_complete,
        'available_stations': available_stations,
        'limit_reached': limit_reached,
    }