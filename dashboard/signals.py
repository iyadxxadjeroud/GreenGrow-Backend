# dashboard/signals.py

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import SensorData, Alert, Greenhouse, Sensor, Actuator, ActuatorStatus
from .constants import DEFAULT_GREENHOUSE_ACTUATORS, ALERT_THRESHOLDS


@receiver(post_save, sender=Sensor)
def create_initial_sensordata(sender, instance, created, **kwargs):
    """
    Signal receiver to create an initial SensorData entry when a new Sensor is created.
    """
    if created:
        print(f"create_initial_sensordata: New Sensor created: {instance.name} (ID: {instance.id}). Creating initial SensorData.")
        # Create an initial SensorData entry for the new sensor
        # You might choose a default value like 0, or None if your field allows it.
        # A value of 0 might be misleading depending on sensor type, but fulfilling the request.
        # Consider if you want data only when the first actual reading arrives.
        SensorData.objects.create(
            sensor=instance,
            value=0.0, # Default value (adjust as needed, e.g., 0.0 for float)
            # timestamp is auto_now_add
            notes="Initial placeholder data on sensor creation."
        )
        print(f"create_initial_sensordata: Initial SensorData created for Sensor ID: {instance.id}.")
    else:
        print(f"create_initial_sensordata: Sensor {instance.name} (ID: {instance.id}) was updated, not creating initial data.")


 # --- New Signal Receiver: Create Initial ActuatorStatus for new Actuators ---
@receiver(post_save, sender=Actuator)
def create_initial_actuatorstatus(sender, instance, created, **kwargs):
    """
    Signal receiver to create an initial ActuatorStatus entry when a new Actuator is created.
    """
    if created:
        print(f"create_initial_actuatorstatus: New Actuator created: {instance.name} (ID: {instance.id}). Creating initial ActuatorStatus.")
        # Create an initial ActuatorStatus entry for the new actuator
        # 'off' is a common default status for actuators
        ActuatorStatus.objects.create(
            actuator=instance,
            status_value='off', # Default status (adjust as needed based on ACTUATOR_TYPES)
            # timestamp is auto_now_add
        )
        print(f"create_initial_actuatorstatus: Initial ActuatorStatus created for Actuator ID: {instance.id}.")
    else:
        print(f"create_initial_actuatorstatus: Actuator {instance.name} (ID: {instance.id}) was updated, not creating initial status.")


@receiver(post_save, sender=SensorData)
def check_sensor_alert(sender, instance, created, **kwargs):
    """
    Signal receiver to check sensor data against predefined thresholds and create/resolve alerts.
    Runs on both creation and update of SensorData.
    """
    # We want this to run on both created and updated instances to check for resolution too
    # if not created:
    #     print("check_sensor_alert: Not a new instance, exiting.")
    #     return

    sensor_data = instance
    sensor = sensor_data.sensor
    greenhouse = sensor.greenhouse
    sensor_type = sensor.type # Corrected field name
    data_value = sensor_data.value # Corrected field name

    print(f"check_sensor_alert: Checking alert for {sensor_type} data: {data_value} in Greenhouse: {greenhouse.name} (ID: {greenhouse.id}) - {'Created' if created else 'Updated'}")

    alert_triggered_by_this_data = False # Flag to see if *this* data point triggers *any* alert

    if sensor_type in ALERT_THRESHOLDS:
        thresholds = ALERT_THRESHOLDS[sensor_type]
        print(f"check_sensor_alert: Thresholds found for {sensor_type}: {thresholds}")

        for condition_type, condition_details in thresholds.items():
            threshold_value = condition_details['threshold']
            alert_message_template = condition_details['message']
            full_alert_message = f"{sensor_type} {alert_message_template.replace('{{ value }}', str(data_value))}"

            print(f"check_sensor_alert: Checking condition '{condition_type}' (Threshold: {threshold_value})")

            is_alert_condition_met = False

            if condition_type == 'greater_than' and data_value > threshold_value:
                is_alert_condition_met = True
                print("check_sensor_alert: 'greater_than' condition met.")
            elif condition_type == 'less_than' and data_value < threshold_value:
                is_alert_condition_met = True
                print("check_sensor_alert: 'less_than' condition met.")
            # Add other condition types here if needed

            # --- Create/Update Alert if condition is met ---
            if is_alert_condition_met:
                alert_triggered_by_this_data = True # Mark that *some* alert is triggered by this data
                print(f"check_sensor_alert: Alert condition met, attempting to get_or_create Alert: {full_alert_message}")
                try:
                    alert, created_alert_obj = Alert.objects.get_or_create(
                        greenhouse=greenhouse,
                        message=full_alert_message,
                        is_resolved=False, # We are looking for/creating an unresolved alert
                        defaults={
                            'severity': 'high',
                            'sensor': sensor, # <-- Now this field exists and can be set
                        }
                    )
                    if created_alert_obj:
                        print(f"check_sensor_alert: !!! New Alert Triggered and Created: Alert ID {alert.id}, Message: {alert.message}")
                    else:
                        print(f"check_sensor_alert: --- Existing Active Alert Found: Alert ID {alert.id}")
                        # Optionally update existing alert's timestamp if needed
                        # alert.created_at = timezone.now()
                        # alert.save(update_fields=['created_at'])

                except Exception as e:
                     print(f"check_sensor_alert: ERROR during Alert.objects.get_or_create: {e}")


        # --- Resolve Alerts if *no* alert condition is met by this data point ---
        # Check if this data point resolves any active alerts for *this specific sensor*.
        if not alert_triggered_by_this_data:
             print(f"check_sensor_alert: No alert condition met by this data point ({data_value}). Checking for resolution for sensor ID {sensor.id}.")
             # Find any active alerts linked to this specific sensor
             # Now we can filter directly using the 'sensor' ForeignKey
             active_alerts_for_sensor = Alert.objects.filter(
                 sensor=sensor, # Filter by the specific sensor
                 is_resolved=False
             )
             if active_alerts_for_sensor.exists():
                 print(f"check_sensor_alert: Found active alerts for sensor ID {sensor.id} to resolve ({active_alerts_for_sensor.count()}).")
                 for alert_to_resolve in active_alerts_for_sensor:
                     # We can refine this further later if needed (e.g., check if the *specific*
                     # condition for this alert message is no longer met).
                     # For now, we resolve any active alert for this sensor.
                     print(f"check_sensor_alert: Attempting to resolve Alert ID {alert_to_resolve.id}: {alert_to_resolve.message}")
                     alert_to_resolve.is_resolved = True
                     alert_to_resolve.save(update_fields=['is_resolved'])
                     print(f"check_sensor_alert: ^^^ Alert Resolved: Alert ID {alert_to_resolve.id}")
             else:
                  print("check_sensor_alert: No active alerts for this sensor to resolve.")
        else:
             print("check_sensor_alert: At least one alert was triggered by this data point, not checking for resolution based on this data.")


    else:
        print(f"check_sensor_alert: No alert thresholds defined for sensor type: {sensor_type}")

    print("check_sensor_alert: Signal finished.")


# --- New Signal Receiver for Sensor Deletion ---
@receiver(pre_delete, sender=Sensor)
def resolve_alerts_on_sensor_delete(sender, instance, **kwargs):
    """
    Signal receiver to resolve active alerts when a Sensor is deleted.
    """
    print(f"resolve_alerts_on_sensor_delete: Sensor {instance.name} (ID: {instance.id}) is being deleted. Resolving related alerts.")
    # Find any active alerts linked to this sensor
    # Using the 'alerts' related_name on the Sensor model
    active_alerts_to_resolve = instance.alerts.filter(is_resolved=False)

    if active_alerts_to_resolve.exists():
        print(f"resolve_alerts_on_sensor_delete: Found active alerts ({active_alerts_to_resolve.count()}) for sensor ID {instance.id} to resolve.")
        for alert_to_resolve in active_alerts_to_resolve:
            print(f"resolve_alerts_on_sensor_delete: Resolving Alert ID {alert_to_resolve.id}: {alert_to_resolve.message}")
            alert_to_resolve.is_resolved = True
            alert_to_resolve.save(update_fields=['is_resolved']) # Use update_fields for efficiency
        print(f"resolve_alerts_on_sensor_delete: All active alerts for sensor ID {instance.id} marked as resolved.")
    else:
        print(f"resolve_alerts_on_sensor_delete: No active alerts found for sensor ID {instance.id} to resolve.")





@receiver(post_save, sender=Greenhouse)
def create_default_sensors(sender, instance, created, **kwargs):
    """
    Signal receiver to create default sensors and initial data when a new Greenhouse is created.
    """
    if created:
        print(f"Creating default sensors for new greenhouse: {instance.name}") # Debug print
        # Liste des capteurs par défaut à créer
        default_sensors = [
            {'type': 'TEMP', 'name': 'Capteur Température'},
            {'type': 'AIR_HUM', 'name': 'Capteur Humidité Air'},
            {'type': 'CO2', 'name': 'Capteur CO2'},
            {'type': 'LIGHT', 'name': 'Capteur Luminosité'},
            {'type': 'SOIL_MOIST', 'name': 'Capteur Humidité Sol'},
            {'type': 'WATER_LVL', 'name': 'Niveau Réservoir'},
            {'type': 'SOLAR_VOLT', 'name': 'Tension Solaire'}
        ]

        # Création des capteurs et données initiales
        default_values = {
            'TEMP': 22.5,
            'AIR_HUM': 65.0,
            'CO2': 400.0,
            'LIGHT': 1000.0,
            'SOIL_MOIST': 30.0,
            'WATER_LVL': 500.0,
            'SOLAR_VOLT': 24.0
        }

        for sensor_data in default_sensors:
            sensor, created = Sensor.objects.get_or_create( # Use get_or_create to avoid creating duplicates if signal fires twice
                greenhouse=instance,
                type=sensor_data['type'], # Use dictionary keys
                defaults={'name': sensor_data['name']} # Set name only on creation
            )
            if created: # Only create initial data if the sensor was just created
                SensorData.objects.create(
                    sensor=sensor,
                    value=default_values.get(sensor.type, 0.0),
                    timestamp=timezone.now()
                )
                print(f" Created sensor: {sensor.name}") # Debug print


@receiver(post_save, sender=Greenhouse)
def create_default_actuators(sender, instance, created, **kwargs):
    """
    Signal receiver to create default actuators and initial status when a new Greenhouse is created.
    """
    if created: # Check if the Greenhouse instance was just created (not updated)
        print(f"Creating default actuators and initial status for new greenhouse: {instance.name}") # Debug print
        for actuator_data in DEFAULT_GREENHOUSE_ACTUATORS:
            # Use get_or_create here as well for robustness
            actuator, actuator_created = Actuator.objects.get_or_create( # Capture the created status and the object
                greenhouse=instance, # Link to the newly created greenhouse
                actuator_type=actuator_data.get('actuator_type'), # Use get for safety
                defaults={'name': actuator_data.get('name', actuator_data.get('actuator_type')), # Use type as default name if name missing
                          'pin_number': actuator_data.get('pin_number', '') # Use get with default for optional fields
                         }
                # Add other fields if necessary
            )

            # If the actuator was just created, create its initial status
            if actuator_created:
                default_status_value = actuator_data.get('default_status', 'unknown') # Get the default status from constants
                ActuatorStatus.objects.create(
                    actuator=actuator, # Link to the newly created actuator
                    status_value=default_status_value,
                    timestamp=timezone.now() # Automatically set by auto_now_add, but explicit is fine
                )
                print(f" Created actuator: {actuator.name} with initial status: {default_status_value}") # Debug print




@receiver(pre_delete, sender=Greenhouse)
def delete_related_objects(sender, instance, **kwargs):
    """
    Signal receiver to explicitly delete related objects before a Greenhouse is deleted.
    (Optional, as CASCADE should handle this, but can be useful for logging or extra actions)
    """
    print(f"Deleting related objects for greenhouse: {instance.name}") # Debug print
    # You might add more explicit deletion logic here if needed,
    # e.g., deleting files, sending external commands, etc.
    # instance.sensors.all().delete() # CASCADE should handle this, so explicit delete is often not needed unless you have special requirements
    # instance.actuators.all().delete() # CASCADE should handle this