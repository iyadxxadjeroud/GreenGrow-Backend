# dashboard/permissions.py (Example adjustment for IsOwner)
from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff # Assuming staff means admin

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request, so we'll always allow GET, HEAD, or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to the owner of the object.
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if the object has a 'greenhouse' attribute which then has a 'user' (e.g., Sensor, Actuator)
        if hasattr(obj, 'greenhouse') and hasattr(obj.greenhouse, 'user'):
            return obj.greenhouse.user == request.user
            
        # Check if the object has an 'actuator' attribute which then has a 'greenhouse' (e.g., ActuatorStatus)
        if hasattr(obj, 'actuator') and hasattr(obj.actuator, 'greenhouse') and hasattr(obj.actuator.greenhouse, 'user'):
            return obj.actuator.greenhouse.user == request.user

        # Fallback: if no specific ownership check applies, deny write access
        return False