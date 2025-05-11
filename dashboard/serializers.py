#dashboard/serializers.py
from rest_framework import serializers
from .models import SensorData, Sensor, Greenhouse, Actuator, ActuatorStatus
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class ActuatorStatusSerializer(serializers.ModelSerializer):
     class Meta:
         model = ActuatorStatus
         fields = ['id', 'actuator', 'timestamp', 'status_value']
         read_only_fields = ['timestamp'] # Timestamp is auto-added

class ActuatorSerializer(serializers.ModelSerializer):
     # Add a field to get the latest status
     latest_status = serializers.SerializerMethodField()

     class Meta:
         model = Actuator
         fields = ['id', 'greenhouse', 'actuator_type', 'name', 'pin_number', 'created_at', 'latest_status']
         read_only_fields = ['created_at'] # created_at is auto-added

     def get_latest_status(self, obj):
         """
         Gets the latest status for this actuator.
         obj is the current Actuator instance.
         """
         try:
             # We used related_name='statuses' in the ActuatorStatus model
             # Order by timestamp descending and get the first one
             latest_status = obj.statuses.latest('timestamp')
             # Serialize the latest status using the ActuatorStatusSerializer
             return ActuatorStatusSerializer(latest_status).data
         except ActuatorStatus.DoesNotExist:
             # Return None or a specific value if no status exists
             return None



class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = '__all__'
        read_only_fields = ['timestamp']

class SensorSerializer(serializers.ModelSerializer):
    # Add a field to include the latest sensor reading
    latest_reading = serializers.SerializerMethodField()

    class Meta:
        model = Sensor
        fields = '__all__' # Or list specific fields, including 'latest_reading'

    # Method to get the latest sensor data for a sensor instance
    def get_latest_reading(self, obj):
        # Fetch the single latest SensorData entry for this sensor
        latest_data = obj.readings.order_by('-timestamp').first()
        if latest_data:
            # Use the SensorDataSerializer to serialize the latest reading
            return SensorDataSerializer(latest_data).data
        return None # Return None if no data found



class GreenhouseSerializer(serializers.ModelSerializer):  # Changer à ModelSerializer
    sensors = SensorSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)  # Utiliser StringRelatedField pour afficher le nom d'utilisateur
    class Meta:
        model = Greenhouse
        fields = ['id', 'name', 'location', 'created_at', 'user', 'sensors']
        read_only_fields = ['user', 'created_at']


# your_app/serializers.py or your_project/serializers.py

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        # Example 1: If role is a field in your user model
        token['role'] = user.role

        # Example 2: If you're using Django groups
        # if user.groups.filter(name='admin').exists():
        #     token['role'] = 'ADMIN'
        # elif user.groups.filter(name='client').exists():
        #     token['role'] = 'CLIENT'
        # else:
        #     token['role'] = 'DEFAULT'

        # Example 3: If you have a separate profile model with a role
        # try:
        #     token['role'] = user.profile.role
        # except AttributeError:
        #     token['role'] = 'DEFAULT'

        return token
    
