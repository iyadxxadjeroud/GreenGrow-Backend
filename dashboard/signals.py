# dashboard/signals.py

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import SensorData, Alert, Greenhouse, Sensor, Actuator, ActuatorStatus
from .constants import DEFAULT_GREENHOUSE_ACTUATORS, ALERT_THRESHOLDS

# Import necessary modules for Channels integration
from channels.layers import get_channel_layer # To get the channel layer instance
from asgiref.sync import async_to_sync # Helper to call async channel layer methods from sync signal
import json # Import json to serialize message data


# --- Get the Channel Layer ---
# Get the channel layer instance once when the signals file is loaded
# We use a try-except block because get_channel_layer will fail if Channels is not configured
try:
    channel_layer = get_channel_layer()
    print("Signals: Successfully got channel layer.")
except Exception as e:
    channel_layer = None
    print(f"Signals: Could not get channel layer: {e}. WebSocket push will not work.")


# --- Your existing signal receivers ---
# This receiver creates an initial SensorData entry when a new Sensor is created.
@receiver(post_save, sender=Sensor)
def create_initial_sensordata(sender, instance, created, **kwargs):
    """
    Signal receiver to create an initial SensorData entry when a new Sensor is created.
    """
    if created:
        print(f"create_initial_sensordata: New Sensor created: {instance.name} (ID: {instance.id}). Creating initial SensorData.")
        try:
            # Ensure we don't create duplicates if the signal is triggered multiple times
            if not SensorData.objects.filter(sensor=instance).exists():
                SensorData.objects.create(
                    sensor=instance,
                    value=0.0, # Default value (adjust as needed, e.g., 0.0 for float)
                    # timestamp is auto_now_add
                    notes="Initial placeholder data on sensor creation."
                )
                print(f"create_initial_sensordata: Initial SensorData created for Sensor ID: {instance.id}.")
            # else: # Can uncomment for debug
            #     print(f"create_initial_sensordata: Initial SensorData already exists for Sensor ID: {instance.id}.")
        except Exception as e:
            print(f"create_initial_sensordata: ERROR creating initial SensorData: {e}")
    # else: # Can uncomment for debug
        # print(f"create_initial_sensordata: Sensor {instance.name} (ID: {instance.id}) was updated, not creating initial data.")


# This receiver creates an initial ActuatorStatus entry when a new Actuator is created.
@receiver(post_save, sender=Actuator)
def create_initial_actuatorstatus(sender, instance, created, **kwargs):
    """
    Signal receiver to create an initial ActuatorStatus entry when a new Actuator is created.
    """
    if created:
        print(f"create_initial_actuatorstatus: New Actuator created: {instance.name} (ID: {instance.id}). Creating initial ActuatorStatus.")
        try:
            # Ensure we don't create duplicates
            if not ActuatorStatus.objects.filter(actuator=instance).exists():
                ActuatorStatus.objects.create(
                    actuator=instance,
                    status_value='off', # Default status (adjust as needed based on ACTUATOR_TYPES)
                    # timestamp is auto_now_add
                )
                print(f"create_initial_actuatorstatus: Initial ActuatorStatus created for Actuator ID: {instance.id}.")
            # else: # Can uncomment for debug
            #     print(f"create_initial_actuatorstatus: Initial ActuatorStatus already exists for Actuator ID: {instance.id}.")
        except Exception as e:
            print(f"create_initial_actuatorstatus: ERROR creating initial ActuatorStatus: {e}")
    # else: # Can uncomment for debug
        # print(f"create_initial_actuatorstatus: Actuator {instance.name} (ID: {instance.id}) was updated, not creating initial status.")


# --- The check_sensor_alert signal receiver (Crucial for WebSocket Push) ---
# This receiver checks sensor data against thresholds and pushes updates via WebSocket.
@receiver(post_save, sender=SensorData)
def check_sensor_alert(sender, instance, created, **kwargs):
    """
    Signal receiver to check sensor data against predefined thresholds and create/resolve alerts.
    Also pushes sensor data updates to the WebSocket channel layer.
    Runs on both creation and update of SensorData.
    """
    sensor_data = instance
    sensor = sensor_data.sensor
    greenhouse = sensor.greenhouse
    sensor_type = sensor.type
    data_value = sensor_data.value

    print(f"check_sensor_alert: Processing {sensor_type} data: {data_value} in Greenhouse: {greenhouse.name} (ID: {greenhouse.id}) - {'Created' if created else 'Updated'}")

    # --- Alert Logic (Ensure your alert creation/resolution logic is here) ---
    # (Based on the code you provided previously, this part seems correct)
    alert_triggered_by_this_data = False # Flag to see if *this* data point triggers *any* alert

    if sensor_type in ALERT_THRESHOLDS:
        thresholds = ALERT_THRESHOLDS[sensor_type]
        # print(f"check_sensor_alert: Thresholds found for {sensor_type}: {thresholds}") # Can uncomment for more debug

        for condition_type, condition_details in thresholds.items():
            threshold_value = condition_details['threshold']
            alert_message_template = condition_details['message']
            full_alert_message = f"{sensor_type} {alert_message_template.replace('{{ value }}', str(data_value))}"

            is_alert_condition_met = False
            if condition_type == 'greater_than' and data_value > threshold_value:
                is_alert_condition_met = True
            elif condition_type == 'less_than' and data_value < threshold_value:
                is_alert_condition_met = True
            # Add other condition types here if needed

            # --- Create/Update Alert if condition is met ---
            if is_alert_condition_met:
                alert_triggered_by_this_data = True
                print(f"check_sensor_alert: Alert condition met, attempting to get_or_create Alert: {full_alert_message}")
                try:
                    alert, created_alert_obj = Alert.objects.get_or_create(
                        greenhouse=greenhouse,
                        message=full_alert_message,
                        is_resolved=False,
                        defaults={
                            'severity': 'high',
                            'sensor': sensor,
                        }
                    )
                    if created_alert_obj:
                        print(f"check_sensor_alert: !!! New Alert Triggered and Created: Alert ID {alert.id}, Message: {alert.message}")
                    # else: # Can uncomment for debug
                    #     print(f"check_sensor_alert: --- Existing Active Alert Found: Alert ID {alert.id}")

                except Exception as e:
                    print(f"check_sensor_alert: ERROR during Alert.objects.get_or_create: {e}")

        # --- Resolve Alerts if *no* alert condition is met by this data point ---
        # Check if this data point resolves any active alerts for *this specific sensor*.
        if not alert_triggered_by_this_data:
            # print(f"check_sensor_alert: No alert condition met by this data point ({data_value}). Checking for resolution for sensor ID {sensor.id}.") # Can uncomment
            # Find any active alerts linked to this specific sensor
            # Using the 'sensor' ForeignKey on the Alert model
            active_alerts_for_sensor = Alert.objects.filter(
                sensor=sensor, # Filter by the specific sensor
                is_resolved=False
            )
            if active_alerts_for_sensor.exists():
                # print(f"check_sensor_alert: Found active alerts for sensor ID {sensor.id} to resolve ({active_alerts_for_sensor.count()}).") # Can uncomment
                for alert_to_resolve in active_alerts_for_sensor:
                    # print(f"check_sensor_alert: Attempting to resolve Alert ID {alert_to_resolve.id}: {alert_to_resolve.message}") # Can uncomment
                    alert_to_resolve.is_resolved = True
                    alert_to_resolve.save(update_fields=['is_resolved']) # Use update_fields for efficiency
                    print(f"check_sensor_alert: ^^^ Alert Resolved: Alert ID {alert_to_resolve.id}")
            # else: # Can uncomment for debug
                # print("check_sensor_alert: No active alerts for this sensor to resolve.")
        # else: # Can uncomment for debug
            # print("check_sensor_alert: At least one alert was triggered by this data point, not checking for resolution based on this data.")


    # else: # Can uncomment for debug
        # print(f"check_sensor_alert: No alert thresholds defined for sensor type: {sensor_type}")


    # --- Push Sensor Data Update to WebSocket Channel Layer ---
    # This is the code that sends the message to the consumer via the channel layer.
    if channel_layer: # Check if channel layer is configured and available
        group_name = f'greenhouse_{greenhouse.id}' # Define the group name based on the greenhouse ID
        # Create a dictionary with the data needed by the frontend
        # This structure should match what the frontend's onmessage handler expects.
        sensor_data_message = {
            'type': 'sensor_data_update', # This must EXACTLY match the handler method name in the consumer (sensor_data_update)
            'message': { # The payload of the message
                'sensor_id': sensor.id, # Include sensor ID so frontend knows which sensor to update
                # Pass the entire latest_reading object structure expected by the frontend state update logic
                'latest_reading': {
                    'value': sensor_data.value, # Include the latest value
                    'timestamp': sensor_data.timestamp.isoformat() # Send timestamp as ISO format string
                },
                'sensor_type': sensor.type, # Include type for frontend unit display (used in SensorValueDisplay)
                'sensor_name': sensor.name, # Include name for frontend if needed
            }
        }
        print(f"check_sensor_alert: Sending sensor update message to group {group_name} with type '{sensor_data_message['type']}'")
        try:
             # Use async_to_sync because signals are synchronous and channel_layer.group_send is asynchronous
             async_to_sync(channel_layer.group_send)(
                 group_name, # Send the message to the specific greenhouse group
                 sensor_data_message # The message dictionary containing type and data
             )
             print(f"check_sensor_alert: Message sent successfully to group {group_name}")
        except Exception as e:
             print(f"check_sensor_alert: ERROR sending message to channel layer group {group_name}: {e}")

    else:
        print("check_sensor_alert: Channel layer not configured. Cannot send WebSocket push.")


    print("check_sensor_alert: Signal finished.")


# --- Other signal receivers below ---
# This receiver resolves active alerts when a Sensor is deleted.
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


# This receiver creates default sensors and initial data when a new Greenhouse is created.
@receiver(post_save, sender=Greenhouse)
def create_default_sensors(sender, instance, created, **kwargs):
    """
    Signal receiver to create default sensors and initial data when a new Greenhouse is created.
    """
    if created: # Check if the Greenhouse instance was just created (not updated)
        print(f"Creating default sensors for new greenhouse: {instance.name}") # Debug print
        # Liste des capteurs par défaut à créer
        default_sensors_data = [
            {'type': 'TEMP', 'name': 'Capteur Température'},
            {'type': 'AIR_HUM', 'name': 'Capteur Humidité Air'},
            {'type': 'CO2', 'name': 'Capteur CO2'},
            {'type': 'LIGHT', 'name': 'Capteur Luminosité'},
            {'type': 'SOIL_MOIST', 'name': 'Capteur Humidité Sol'},
            {'type': 'WATER_LVL', 'name': 'Niveau Réservoir'},
            {'type': 'SOLAR_VOLT', 'name': 'Tension Solaire'}
        ]
        default_values = {
            'TEMP': 22.5,
            'AIR_HUM': 65.0,
            'CO2': 400.0,
            'LIGHT': 1000.0,
            'SOIL_MOIST': 30.0,
            'WATER_LVL': 500.0,
            'SOLAR_VOLT': 24.0
        }

        # Création des capteurs et données initiales
        for sensor_data in default_sensors_data:
            try:
                sensor, created_sensor = Sensor.objects.get_or_create( # Use get_or_create to avoid creating duplicates if signal fires twice
                    greenhouse=instance,
                    type=sensor_data['type'], # Use dictionary keys
                    defaults={'name': sensor_data['name']} # Set name only on creation
                )
                if created_sensor: # Only create initial data if the sensor was just created
                    print(f" Created sensor: {sensor.name} (ID: {sensor.id}).")
                    # Create initial SensorData for this new sensor
                    try:
                        # Check if initial SensorData already exists for this sensor
                        if not SensorData.objects.filter(sensor=sensor).exists():
                            SensorData.objects.create(
                                sensor=sensor,
                                value=default_values.get(sensor.type, 0.0),
                                timestamp=timezone.now()
                            )
                            print(f"  Created initial SensorData for Sensor ID: {sensor.id}.")
                        # else: # Can uncomment for debug
                         #    print(f"  Initial SensorData already exists for Sensor ID: {sensor.id}. Skipping creation.")

                    except Exception as e:
                        print(f"  ERROR creating initial SensorData for Sensor ID {sensor.id}: {e}")
                # else: # Can uncomment for debug
                #     print(f" Sensor {sensor.name} (ID: {sensor.id}) already exists for this greenhouse.")
            except Exception as e:
                 print(f" ERROR creating sensor {sensor_data.get('name', sensor_data.get('type'))}: {e}")


# This receiver creates default actuators and initial status when a new Greenhouse is created.
@receiver(post_save, sender=Greenhouse)
def create_default_actuators(sender, instance, created, **kwargs):
    """
    Signal receiver to create default actuators and initial status when a new Greenhouse is created.
    """
    if created: # Check if the Greenhouse instance was just created (not updated)
        print(f"Creating default actuators and initial status for new greenhouse: {instance.name}") # Debug print
        for actuator_data in DEFAULT_GREENHOUSE_ACTUATORS:
            try:
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
                    print(f" Created actuator: {actuator.name} (ID: {actuator.id}).")
                    default_status_value = actuator_data.get('default_status', 'unknown') # Get the default status from constants
                    try:
                        # Check if initial ActuatorStatus already exists for this actuator
                        if not ActuatorStatus.objects.filter(actuator=actuator).exists():
                            ActuatorStatus.objects.create(
                                actuator=actuator, # Link to the newly created actuator
                                status_value=default_status_value,
                                timestamp=timezone.now() # Automatically set by auto_now_add, but explicit is fine
                            )
                            print(f"  Created initial status '{default_status_value}' for Actuator ID: {actuator.id}.")
                        # else: # Can uncomment for debug
                        #     print(f"  Initial ActuatorStatus already exists for Actuator ID: {actuator.id}. Skipping creation.")

                    except Exception as e:
                        print(f"  ERROR creating initial ActuatorStatus for Actuator ID {actuator.id}: {e}")
                # else: # Can uncomment for debug
                #     print(f" Actuator {actuator.name} (ID: {actuator.id}) already exists for this greenhouse.")
            except Exception as e:
                 print(f" ERROR creating actuator {actuator_data.get('name', actuator_data.get('actuator_type'))}: {e}")


# This receiver explicitly deletes related objects before a Greenhouse is deleted.
@receiver(pre_delete, sender=Greenhouse)
def delete_related_objects(sender, instance, **kwargs):
    """
    Signal receiver to explicitly delete related objects before a Greenhouse is deleted.
    (Optional, as CASCADE should handle this, but can be useful for logging or extra actions)
    """
    print(f"Deleting related objects for greenhouse: {instance.name} (ID: {instance.id})") # Debug print
    # CASCADE should handle this, so explicit deletion is often not needed
    # unless you have specific requirements like custom cleanup logic.
    # Example if you needed custom logic before deletion:
    # print("  Explicitly deleting sensors...")
    # for sensor in instance.sensors.all():
    #     print(f"    Deleting sensor: {sensor.name} (ID: {sensor.id})")
    #     try:
    #         sensor.delete() # This would trigger pre_delete on Sensor
    #     except Exception as e:
    #         print(f"    ERROR deleting sensor {sensor.id}: {e}")

    # print("  Explicitly deleting actuators...")
    # for actuator in instance.actuators.all():
    #     print(f"    Deleting actuator: {actuator.name} (ID: {actuator.id})")
    #     try:
    #         actuator.delete() # This would trigger pre_delete on Actuator
    #     except Exception as e:
    #         print(f"    ERROR deleting actuator {actuator.id}: {e}")

    print("Finished delete_related_objects signal.")