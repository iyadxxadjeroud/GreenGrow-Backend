# dashboard/constants.py

ACTUATOR_TYPES = [
     ('watering_valve', 'Watering Valve'),
     ('ventilation_fan', 'Ventilation Fan'),
     ('heating_element', 'Heating Element'),
     ('cooling_unit', 'Cooling Unit'),
     ('light', 'Light'), # Example for grow lights
     # Add other actuator types as needed
 ]

# Define default actuators to create with each new greenhouse
# Format: {'actuator_type': '...', 'name': '...', 'pin_number': '...'} (pin_number is optional)
DEFAULT_GREENHOUSE_ACTUATORS = [
    {'actuator_type': 'watering_valve', 'name': 'Main Watering Valve', 'default_status': 'off'},
    {'actuator_type': 'ventilation_fan', 'name': 'Primary Ventilation Fan', 'default_status': '0%'},
    {'actuator_type': 'heating_element', 'name': 'Heater', 'default_status': 'off'},
    {'actuator_type': 'cooling_unit', 'name': 'Cooling Unit', 'default_status': 'off'},
    {'actuator_type': 'light', 'name': 'Grow Lights', 'default_status': 'off'},
    # Add other default actuators as needed, with a default_status
]
ALERT_THRESHOLDS = {
    'TEMP': { # Corrected key
        'greater_than': {'threshold': 30.0, 'message': 'High Temperature Alert: Temperature is {{ value }}°C'},
        'less_than': {'threshold': 10.0, 'message': 'Low Temperature Alert: Temperature is {{ value }}°C'},
    },
    'AIR_HUM': { # Corrected key
        'greater_than': {'threshold': 80.0, 'message': 'High Humidity Alert: Humidity is {{ value }}%'},
        'less_than': {'threshold': 30.0, 'message': 'Low Humidity Alert: Humidity is {{ value }}%'},
    },
    'CO2': { # Corrected key (was 'co2')
        'greater_than': {'threshold': 1000.0, 'message': 'High CO2 Level Alert: CO2 is {{ value }} ppm'},
    },
    'LIGHT': { # Corrected key
         'less_than': {'threshold': 200.0, 'message': 'Low Light Level Alert: Light is {{ value }} lux'},
    },
    'SOIL_MOIST': { # Add if you have thresholds
        # Define soil moisture thresholds
    },
    'SOIL_TEMP': { # Add if you have thresholds
        # Define soil temperature thresholds
    },
    'WATER_LVL': { # Add if you have thresholds
        # Define water level thresholds
    },
    'SOLAR_VOLT': { # Add if you have thresholds
        # Define solar voltage thresholds
    }
    # Add thresholds for other sensor types as needed
}
