from rest_framework import serializers, viewsets, routers
from django.apps import apps

# Get all models from the wrsms app
app_models = apps.get_app_config('wrsm_app').get_models()

router = routers.DefaultRouter()

for model in app_models:
    # Create serializer dynamically
    serializer_meta = type('Meta', (), {'model': model, 'fields': '__all__'})
    serializer_class = type(f'{model.__name__}Serializer', (serializers.ModelSerializer,), {'Meta': serializer_meta})

    # Create viewset dynamically
    viewset_class = type(f'{model.__name__}ViewSet', (viewsets.ModelViewSet,), {
        'queryset': model.objects.all(),
        'serializer_class': serializer_class,
    })

    # Register the viewset
    router.register(model.__name__.lower(), viewset_class)
