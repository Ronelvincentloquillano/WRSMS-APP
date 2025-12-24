from .models import StationSetting

def global_context(request):
    has_station_settings = False
    settings_complete = False
    station = {'name':'Admin Water Refilling Station','id':0}

    if not request.user.is_authenticated:
        return {
            'has_station_settings': has_station_settings,
            'settings_complete': settings_complete
        }

    profile = getattr(request.user, 'profile', None)

    if profile:
        station = profile.station
        try:
            station_settings = StationSetting.objects.get(station=station)
            has_station_settings = True
            
            required_fields = [
                station_settings.default_delivery_rate,
                station_settings.default_jug_size,
                station_settings.default_unit_price,
                station_settings.default_minimum_delivery_qty,
                station_settings.default_order_type,
                station_settings.default_payment_type
            ]
            settings_complete = all(field is not None for field in required_fields)
            
        except StationSetting.DoesNotExist:
            pass
    
    available_stations = []
    if profile and profile.allowed_stations.count() > 1:
        available_stations = profile.allowed_stations.all()

    return {
        'station': station,
        'has_station_settings': has_station_settings,
        'settings_complete': settings_complete,
        'available_stations': available_stations,
    }