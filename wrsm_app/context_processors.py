from .models import StationSetting

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
        except StationSetting.DoesNotExist:
            pass
    
    available_stations = []
    if profile and profile.allowed_stations.count() > 1:
        available_stations = profile.allowed_stations.all()

    return {
        'station': station,
        'has_station_settings': has_station_settings,
        'available_stations': available_stations,
    }