#dashboard/models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from .constants import ACTUATOR_TYPES # We'll define this constant


class User(AbstractUser):
    ROLE_CHOICES = [
        ('FARMER', 'Farmer'),
        ('TECH', 'Technician'), 
        ('ADMIN', 'Admin')
    ]
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='FARMER',
        help_text="Définit les droits d'accès"
    )

    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User GreenGrow'
    

class Greenhouse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='greenhouses') 
    name = models.CharField(max_length=100, help_text="E.g.: Greenhouse A")
    location = models.CharField(max_length=100, help_text="E.g.: Building 3, Zone 5")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.location})"
    @property
    def sensor_count(self):
        return self.sensors.count()

class Actuator(models.Model):
     greenhouse = models.ForeignKey(Greenhouse, on_delete=models.CASCADE, related_name='actuators') # Related name for reverse access
     actuator_type = models.CharField(max_length=50, choices=ACTUATOR_TYPES) # Use choices for known types
     name = models.CharField(max_length=100, help_text="Human-readable name for the actuator")
     pin_number = models.CharField(max_length=20, blank=True, help_text="Physical pin or identifier if applicable")
     created_at = models.DateTimeField(auto_now_add=True)

     def __str__(self):
         return f"{self.name} ({self.actuator_type}) in {self.greenhouse.name}"

class ActuatorStatus(models.Model):
     actuator = models.ForeignKey(Actuator, on_delete=models.CASCADE, related_name='statuses') # Related name for reverse access
     timestamp = models.DateTimeField(auto_now_add=True)
     status_value = models.CharField(max_length=255, help_text="The state or command value (e.g., 'on', 'off', '50%', 'open')") # Using CharField for flexibility

     class Meta:
         ordering = ['-timestamp'] # Order by latest status first

     def __str__(self):
         return f"{self.actuator.name} status at {self.timestamp}: {self.status_value}"

class Sensor(models.Model):
    SENSOR_TYPES = [
        ('TEMP', 'Air Temperature (°C)'),
        ('AIR_HUM', 'Air Humidity (% RH)'),
        ('CO2', 'CO2 Level(ppm)'),
        ('LIGHT', 'Light Intensity(Lux)'),
        ('SOIL_MOIST', 'Soil Moisture (% VWC)'),
        ('SOIL_TEMP', 'Soil Temperature (°C)'),
        ('WATER_LVL', 'Water Tank Level (L)'),
        ('SOLAR_VOLT', 'Solar Voltage (V)'),
    ]
    greenhouse = models.ForeignKey(Greenhouse, on_delete=models.CASCADE, db_index= True, related_name='sensors')
    type = models.CharField(max_length=15, choices=SENSOR_TYPES)
    name = models.CharField(max_length=50, help_text="E.g.: Tomato Zone Sensor")
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"{self.get_type_display()} Sensor"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"
    
class SensorData(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='readings')
    value = models.FloatField(help_text="Raw sensor value")
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Optional calibration notes")

    class Meta:
        ordering = ['-timestamp']  # Newest first

    def __str__(self):
        return f"{self.sensor.name}: {self.value} at {self.timestamp}"
    
class Alert(models.Model):
    greenhouse = models.ForeignKey(Greenhouse, on_delete=models.CASCADE, related_name='alerts')
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    message = models.CharField(max_length=255, help_text="Alert message")
    severity = models.CharField(max_length=10, choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('CRITICAL', 'Critical')])
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False, help_text="Indicates if the alert has been resolved")

    def __str__(self):
        return f"Alert for {self.greenhouse.name}: {self.message} ({'Resolved' if self.is_resolved else 'Active'})"

    class Meta:
        ordering = ['-created_at'] # Order by newest alerts first

