from rest_framework import serializers, viewsets, routers
from django.apps import apps
from django.contrib.auth.models import User, Group

# Get all models from the wrsms app
app_models = list(apps.get_app_config('wrsm_app').get_models())

# Add Auth models
app_models.append(User)
app_models.append(Group)

router = routers.DefaultRouter()

for model in app_models:
    # Create serializer dynamically
    if model == User:
         # Exclude password
         serializer_meta = type('Meta', (), {'model': model, 'exclude': ['password']})
    else:
         serializer_meta = type('Meta', (), {'model': model, 'fields': '__all__'})
    
    serializer_class = type(f'{model.__name__}Serializer', (serializers.ModelSerializer,), {'Meta': serializer_meta})

    # Create viewset dynamically
    viewset_class = type(f'{model.__name__}ViewSet', (viewsets.ModelViewSet,), {
        'queryset': model.objects.all(),
        'serializer_class': serializer_class,
    })

    # Register the viewset
    router.register(model.__name__.lower(), viewset_class)