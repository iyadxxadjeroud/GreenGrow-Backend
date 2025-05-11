# dashboard/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers # Assuming you use drf-nested-routers

from .views import (
    GreenhouseViewSet,
    SensorViewSet,
    SensorDataViewSet,
    ActuatorViewSet,
    ActuatorStatusViewSet,
    GreenhouseOverview, # Your existing overview view
)

# Use DefaultRouter for top-level viewsets
router = DefaultRouter()
router.register(r'greenhouses', GreenhouseViewSet, basename='greenhouse')

# Create a nested router for sensors under greenhouses
greenhouses_router = routers.NestedSimpleRouter(router, r'greenhouses', lookup='greenhouse')
greenhouses_router.register(r'sensors', SensorViewSet, basename='greenhouse-sensors')

# Create a further nested router for sensor data under sensors
sensors_router = routers.NestedSimpleRouter(greenhouses_router, r'sensors', lookup='sensor')
sensors_router.register(r'data', SensorDataViewSet, basename='sensor-data')

# Create a nested router for actuators under greenhouses
greenhouses_router.register(r'actuators', ActuatorViewSet, basename='greenhouse-actuators')

# Create a further nested router for actuator status under actuators
actuators_router = routers.NestedSimpleRouter(greenhouses_router, r'actuators', lookup='actuator')
actuators_router.register(r'status', ActuatorStatusViewSet, basename='actuator-status')


# Define app_name if you use namespaced URLs
app_name = 'dashboard'

urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)), # Includes /greenhouses/

    # Include nested router URLs
    path('', include(greenhouses_router.urls)), # Includes /greenhouses/{greenhouse_pk}/sensors/ and /greenhouses/{greenhouse_pk}/actuators/
    path('', include(sensors_router.urls)), # Includes /greenhouses/{greenhouse_pk}/sensors/{sensor_pk}/data/
    path('', include(actuators_router.urls)), # Includes /greenhouses/{greenhouse_pk}/actuators/{actuator_pk}/status/


    # Custom overview endpoint (make sure this path is correct and matches your urls.py)
    path('greenhouses/<int:greenhouse_id>/overview/', GreenhouseOverview.as_view(), name='greenhouse-overview'),

    # Add other custom URLs if you have them
]