from .models import StationSetting, Customer

def global_context(request):
    has_station_settings = False
    station = {'name':'Admin Water Refilling Station','id':0}

    if not request.user.is_authenticated:
        return {'has_station_settings': has_station_settings}

    profile = getattr(request.user, 'profile', None)

    if profile:
        station = profile.station
        try:
            station_settings = StationSetting.objects.get(station=station)
            has_station_settings = True
            customer_count = Customer.objects.filter(station=station).count()
        except StationSetting.DoesNotExist:
            pass

    return {
        'station': station,
        'has_station_settings': has_station_settings,
        'customer_count': customer_count,
    }