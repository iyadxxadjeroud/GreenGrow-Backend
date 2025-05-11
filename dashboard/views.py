# dashboard/views.py
from rest_framework import viewsets, permissions
from django.core.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Sensor, SensorData, Greenhouse, Actuator, ActuatorStatus
from .serializers import SensorSerializer, SensorDataSerializer, GreenhouseSerializer, ActuatorSerializer, ActuatorStatusSerializer
from .permissions import IsAdminOrReadOnly, IsOwner
from django.shortcuts import render
from django.db.models import Prefetch
from rest_framework.response import Response
import pdb



# ------------ Sensor ViewSet ------------
class SensorViewSet(viewsets.ModelViewSet):
    serializer_class = SensorSerializer
    queryset = Sensor.objects.select_related(
        'greenhouse'
    ).prefetch_related('readings').all()
    
    def get_queryset(self):
        return Sensor.objects.filter(
            greenhouse_id=self.kwargs['greenhouse_pk'],
            greenhouse__user=self.request.user
        )
    
    def perform_create(self, serializer):
        greenhouse = Greenhouse.objects.get(pk=self.kwargs['greenhouse_pk']) # Corrected line
        if greenhouse.user != self.request.user:
            raise PermissionDenied("You do not own this greenhouse.")
        serializer.save(greenhouse=greenhouse) # Corrected line


class SensorDataViewSet(viewsets.ModelViewSet):
    serializer_class = SensorDataSerializer

    def get_queryset(self):
        return SensorData.objects.filter(
            sensor_id=self.kwargs['sensor_pk'],
            sensor__greenhouse__user_id=self.request.user.id
        )
    

class GreenhouseViewSet(viewsets.ModelViewSet):
    serializer_class = GreenhouseSerializer
    permission_classes = [IsAdminOrReadOnly | IsOwner]
    queryset = Greenhouse.objects.prefetch_related(
        Prefetch('sensors', queryset=Sensor.objects.all().prefetch_related('readings'))
    ).all()

    # Add pdb.set_trace() here
    # Override the dispatch method temporarily for debugging
    def dispatch(self, request, *args, **kwargs):
        print("--- In GreenhouseViewSet dispatch ---") # Debug print
        
        return super().dispatch(request, *args, **kwargs)

    # Or alternatively, place it at the start of the list method
    # def list(self, request, *args, **kwargs):
    #     print("--- In GreenhouseViewSet list ---") # Debug print
    #     pdb.set_trace() # <-- Add this line
    #     return super().list(request, *args, **kwargs)


    def get_queryset(self):
        # This is where the error happens if request.user is AnonymousUser
        print(f"--- In GreenhouseViewSet get_queryset. Request User: {self.request.user} ---") # Debug print
        return Greenhouse.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        greenhouse = serializer.save(user=self.request.user)
     

class ActuatorViewSet(viewsets.ModelViewSet):
    serializer_class = ActuatorSerializer
    permission_classes = [IsAuthenticated, IsOwner] # Use IsOwner for object-level permissions

    def get_queryset(self):
        """
        Returns actuators belonging to the specified greenhouse and owned by the requesting user.
        """
        return Actuator.objects.filter(
            greenhouse_id=self.kwargs['greenhouse_pk'], # 'greenhouse_pk' comes from nested URL
            greenhouse__user=self.request.user
        ).select_related('greenhouse').prefetch_related('statuses') # Pre-fetch statuses for latest_status field

    def perform_create(self, serializer):
        """
        Ensures the created actuator is linked to the correct greenhouse and owned by the user.
        """
        try:
            greenhouse = Greenhouse.objects.get(
                pk=self.kwargs['greenhouse_pk'],
                user=self.request.user
            )
        except Greenhouse.DoesNotExist:
            raise PermissionDenied("Greenhouse not found or you do not own it.")

        serializer.save(greenhouse=greenhouse)


class ActuatorStatusViewSet(viewsets.ModelViewSet):
    serializer_class = ActuatorStatusSerializer
    permission_classes = [IsAuthenticated, IsOwner] # Or a specific permission for creating statuses

    def get_queryset(self):
        """
        Returns status updates for a specific actuator, ensuring the user owns the greenhouse.
        """
        return ActuatorStatus.objects.filter(
            actuator_id=self.kwargs['actuator_pk'], # 'actuator_pk' comes from nested URL
            actuator__greenhouse__user=self.request.user # Ensure user owns the greenhouse
        ).select_related('actuator') # Select related actuator to avoid extra queries

    def perform_create(self, serializer):
        """
        Ensures the status is linked to the correct actuator and the user owns the greenhouse.
        """
        try:
            actuator = Actuator.objects.get(
                pk=self.kwargs['actuator_pk'],
                greenhouse__user=self.request.user # Check ownership via greenhouse
            )
        except Actuator.DoesNotExist:
            raise PermissionDenied("Actuator not found or you do not own the greenhouse.")

        serializer.save(actuator=actuator)

class GreenhouseOverview(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, greenhouse_id):
        try:
            greenhouse = Greenhouse.objects.get(pk=greenhouse_id, user=request.user)
        except Greenhouse.DoesNotExist:
            return Response({'error': 'Greenhouse not found.'}, status=status.HTTP_404_NOT_FOUND)

        # --- Fetch Actuators and their latest statuses ---
        # Prefetch 'statuses' for the ActuatorSerializer's 'latest_status' field to avoid N+1 queries
        actuators_queryset = Actuator.objects.filter(greenhouse=greenhouse).prefetch_related(
            Prefetch('statuses', queryset=ActuatorStatus.objects.order_by('-timestamp'))
        )
        # Serialize the actuators
        actuators_data = ActuatorSerializer(actuators_queryset, many=True).data

        # --- Fetch Alerts ---
        # If you have an Alert model linked to Greenhouse:
        # Make sure your Alert model has a ForeignKey to Greenhouse and a 'message' field
        # If you don't have an Alert model yet, or it's structured differently, this line will cause an error.
        # You might want to define a simple Alert model like:
        # class Alert(models.Model):
        #     greenhouse = models.ForeignKey(Greenhouse, on_delete=models.CASCADE, related_name='alerts')
        #     message = models.TextField()
        #     is_active = models.BooleanField(default=True)
        #     timestamp = models.DateTimeField(auto_now_add=True)
        #
        try:
            alerts = greenhouse.alerts.filter(is_resolved=False).values_list('message', flat=True)
            alerts_data = list(alerts)
        except AttributeError:
            # This means greenhouse.alerts does not exist, e.g., no Alert model or ForeignKey
            print("Warning: 'alerts' relationship not found on Greenhouse model. Skipping alerts.")
            alerts_data = [] # Default to empty list if alerts relationship doesn't exist

        overview_data = {
            'id': greenhouse.id,
            'name': greenhouse.name,
            'location': greenhouse.location, # Include location too, as it's useful for overview
            'actuators': actuators_data, # Now it's a list of serialized actuator objects
            'alerts': alerts_data,
            # Add other relevant basic info here, like sensor_count if you add it to serializer
        }

        return Response(overview_data)