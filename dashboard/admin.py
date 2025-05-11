# dashboard/admin.py

from django.db.models import Prefetch
from django.urls import reverse # Ensure reverse is imported
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html # Ensure format_html is imported
from .models import Greenhouse, Sensor, SensorData, User, Actuator, ActuatorStatus, Alert
from django_admin_listfilter_dropdown.filters import DropdownFilter
from advanced_filters.admin import AdminAdvancedFiltersMixin


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role',)}),
    )

# Inline for SensorData (nested under Sensor)
class SensorDataInline(admin.TabularInline):
    model = SensorData
    extra = 0
    readonly_fields = ['timestamp']
    fields = ['value', 'timestamp', 'notes']

# Inline for Sensors (nested under Greenhouse)
class SensorInline(admin.TabularInline):
    model = Sensor
    extra = 0
    show_change_link = True
    fk_name = 'greenhouse'

# --- New Inlines for Actuators and ActuatorStatus ---

# Inline for ActuatorStatus (nested under Actuator)
class ActuatorStatusInline(admin.TabularInline):
    model = ActuatorStatus
    extra = 0
    readonly_fields = ['timestamp']
    fields = ['status_value', 'timestamp']


# Inline for Actuators (nested under Greenhouse)
class ActuatorInline(admin.TabularInline):
    model = Actuator
    extra = 0
    show_change_link = True
    fk_name = 'greenhouse'


@admin.register(Greenhouse)
class GreenhouseAdmin(AdminAdvancedFiltersMixin, admin.ModelAdmin):
    search_fields = ['name', 'user__username']

    # Method to create a link to the user - Already correctly formatted as link
    def user_link(self, obj):
        try:
            user_admin_url = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', user_admin_url, obj.user.username)
        except Exception:
            return obj.user.username
    user_link.short_description = 'Utilisateur'

    # Custom display for sensors tree (assuming it works as intended)
    def sensors_tree(self, obj):
        sensors = obj.sensors.all()
        html = "<ul class='tree'>"
        for sensor in sensors:
            html += f"""
            <li class='sensor-node'>
                🌡️ {sensor.name}
                <span class='sensor-type'>{sensor.get_type_display()}</span>
                <ul class='data-list'>
                    {"".join(
                        f"<li>📊 {data.value} <small>{data.timestamp}</small></li>"
                        for data in sensor.readings.all()
                    )}
                </ul>
            </li>
            """
        html += "</ul>"
        return format_html(html)

    sensors_tree.short_description = "Capteurs et Données"


    list_display = ('name', 'user_link', 'location', 'sensors_tree')

    list_filter = (
        'user',
        'location',
        'created_at'
    )
    inlines = [SensorInline, ActuatorInline]
    advanced_filter_fields = (
        ('user__username', 'Propriétaire'),
        ('location', 'icontains'),
        ('created_at', ('year', 'month')),
        ('sensors__type', 'Type de capteur installé'),
        ('actuators__actuator_type', 'Type d\'actionneur installé'),
    )
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related(
            Prefetch('sensors', queryset=Sensor.objects.all().prefetch_related('readings')),
            'actuators'
        )

    class Media:
        css = {
            'all': ('css/admin_tree.css',)
        }

@admin.register(Sensor)
class SensorAdmin(AdminAdvancedFiltersMixin, admin.ModelAdmin):
    search_fields = ['name', 'type', 'greenhouse__name', 'greenhouse__user__username']
    list_filter = (
        ('greenhouse', admin.RelatedOnlyFieldListFilter),
        ('type', DropdownFilter),
        'is_active',
        ('greenhouse__user', admin.RelatedOnlyFieldListFilter),
    )
    list_display = ('name', 'greenhouse_user', 'clickable_greenhouse', 'type', 'is_active')
    inlines = [SensorDataInline]
    advanced_filter_fields = (
        ('type', 'Type de capteur'),
        ('greenhouse__name', 'Nom de la serre'),
        ('is_active', 'Statut actif/inactif'),
        ('greenhouse__user__username', 'Propriétaire'),
        #('last_update', ('gt', 'lt')),
    )
    autocomplete_fields = ['greenhouse']
    ordering = ['greenhouse__user__username', 'greenhouse', 'name']
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('greenhouse__user')

    # Method to display the username of the greenhouse owner as a clickable link
    def greenhouse_user(self, obj):
        user = obj.greenhouse.user if obj.greenhouse else None
        # Removed debug prints
        if user:
            try:
                # Use the correct admin URL name for User change in your setup
                user_admin_url = reverse("admin:dashboard_user_change", args=[user.id])
                return format_html('<a href="{}">{}</a>', user_admin_url, user.username)
            except Exception:
                return user.username # Fallback to username if reverse fails
        return '-' # Display '-' if greenhouse or user is None
    greenhouse_user.short_description = 'User'

    def clickable_greenhouse(self, obj):
        greenhouse = obj.greenhouse
        if greenhouse:
            try:
                # Use the correct admin URL name for Greenhouse change in your setup
                greenhouse_admin_url = reverse("admin:dashboard_greenhouse_change", args=[greenhouse.id])
                return format_html('<a href="{}">{}</a>', greenhouse_admin_url, greenhouse.name)
            except Exception:
                return greenhouse.name # Fallback
        return '-' # Display '-' if greenhouse is None
    clickable_greenhouse.short_description = 'Greenhouse' # Set the column header



@admin.register(SensorData)
class SensorDataAdmin(AdminAdvancedFiltersMixin, admin.ModelAdmin):
    search_fields = ['sensor__name', 'sensor__greenhouse__name', 'sensor__greenhouse__user__username', 'value']
    list_display = ('sensor', 'greenhouse_user', 'value', 'timestamp')
    list_filter = (
        ('sensor__greenhouse', admin.RelatedOnlyFieldListFilter),
        'timestamp',
        ('sensor__greenhouse__user', admin.RelatedOnlyFieldListFilter),
    )
    advanced_filter_fields = (
        ('sensor__name', 'Nom du capteur'),
        ('value', ('exact', 'gt', 'lt')),
        ('timestamp', 'Date'),
        ('sensor__greenhouse__user__username', 'Propriétaire'),
    )
    # Method to display the username of the greenhouse owner as a clickable link
    def greenhouse_user(self, obj):
        user = obj.sensor.greenhouse.user if obj.sensor and obj.sensor.greenhouse else None
        # Removed debug prints
        if user:
            try:
                # Use the correct admin URL name for User change in your setup
                user_admin_url = reverse("admin:dashboard_user_change", args=[user.id])
                return format_html('<a href="{}">{}</a>', user_admin_url, user.username)
            except Exception:
                return user.username
        return '-'
    greenhouse_user.short_description = 'User'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sensor__greenhouse__user')


# Register the Actuator model
@admin.register(Actuator)
class ActuatorAdmin(AdminAdvancedFiltersMixin, admin.ModelAdmin):
    search_fields = ['name', 'actuator_type', 'greenhouse__name', 'greenhouse__user__username']
    list_filter = (
        ('greenhouse', admin.RelatedOnlyFieldListFilter),
        ('actuator_type', DropdownFilter),
        ('greenhouse__user', admin.RelatedOnlyFieldListFilter),
    )
    list_display = ('name', 'greenhouse_user', 'clickable_greenhouse', 'actuator_type', 'latest_status_display')

    inlines = [ActuatorStatusInline]
    advanced_filter_fields = (
        ('actuator_type', 'Type d\'actionneur'),
        ('greenhouse__name', 'Nom de la serre'),
        ('greenhouse__user__username', 'Propriétaire'),
    )
    autocomplete_fields = ['greenhouse']
    ordering = ['greenhouse__user__username', 'greenhouse', 'name']
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('greenhouse__user').prefetch_related(
            Prefetch('statuses', queryset=ActuatorStatus.objects.order_by('-timestamp'))
        )

    # Method to display the latest status in the list_display
    def latest_status_display(self, obj):
        try:
            latest = obj.statuses.latest('timestamp')
            return f"{latest.status_value} ({latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
        except ActuatorStatus.DoesNotExist:
            return "No status yet"
    latest_status_display.short_description = "Dernier Statut"

    # Method to display the username of the greenhouse owner as a clickable link
    def greenhouse_user(self, obj):
        user = obj.greenhouse.user if obj.greenhouse else None
        # Removed debug prints
        if user:
            try:
                # Use the correct admin URL name for User change in your setup
                user_admin_url = reverse("admin:dashboard_user_change", args=[user.id])
                return format_html('<a href="{}">{}</a>', user_admin_url, user.username)
            except Exception:
                return user.username
        return '-'
    greenhouse_user.short_description = 'User'

    def clickable_greenhouse(self, obj):
        greenhouse = obj.greenhouse
        if greenhouse:
            try:
                # Use the correct admin URL name for Greenhouse change in your setup
                greenhouse_admin_url = reverse("admin:dashboard_greenhouse_change", args=[greenhouse.id])
                return format_html('<a href="{}">{}</a>', greenhouse_admin_url, greenhouse.name)
            except Exception:
                return greenhouse.name # Fallback
        return '-' # Display '-' if greenhouse is None
    clickable_greenhouse.short_description = 'Greenhouse' # Set the column header



# Register the ActuatorStatus model
@admin.register(ActuatorStatus)
class ActuatorStatusAdmin(AdminAdvancedFiltersMixin, admin.ModelAdmin):
    search_fields = ['actuator__name', 'actuator__greenhouse__name', 'status_value', 'actuator__greenhouse__user__username']
    list_display = ('actuator', 'greenhouse_user', 'status_value', 'timestamp')
    list_filter = (
        ('actuator__greenhouse', admin.RelatedOnlyFieldListFilter),
        ('actuator', admin.RelatedOnlyFieldListFilter),
        'timestamp',
        ('actuator__greenhouse__user', admin.RelatedOnlyFieldListFilter),
    )
    advanced_filter_fields = (
        ('actuator__name', 'Nom de l\'actionneur'),
        ('status_value', 'Statut'),
        ('timestamp', 'Date'),
        ('actuator__greenhouse__user__username', 'Propriétaire'),
    )
    # Method to display the username of the greenhouse owner as a clickable link
    def greenhouse_user(self, obj):
        user = obj.actuator.greenhouse.user if obj.actuator and obj.actuator.greenhouse else None
        # Removed debug prints
        if user:
            try:
                # Use the correct admin URL name for User change in your setup
                user_admin_url = reverse("admin:dashboard_user_change", args=[user.id])
                return format_html('<a href="{}">{}</a>', user_admin_url, user.username)
            except Exception:
                return user.username
        return '-'
    greenhouse_user.short_description = 'User'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('actuator__greenhouse__user')

# Register the Alert model
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('message', 'clickable_greenhouse', 'sensor', 'severity', 'created_at', 'is_resolved')
    list_filter = (
        ('greenhouse', admin.RelatedOnlyFieldListFilter),
        ('sensor', admin.RelatedOnlyFieldListFilter),
        'severity',
        'is_resolved',
        'created_at',
    )
    search_fields = ['message', 'greenhouse__name', 'sensor__name']
    list_editable = ['is_resolved']
    actions = ['mark_as_resolved']

    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
        self.message_user(request, "Selected alerts have been marked as resolved.")
    mark_as_resolved.short_description = "Mark selected alerts as resolved"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sensor', 'greenhouse')
    
    def clickable_greenhouse(self, obj):
        greenhouse = obj.greenhouse
        if greenhouse:
            try:
                # Use the correct admin URL name for Greenhouse change in your setup
                greenhouse_admin_url = reverse("admin:dashboard_greenhouse_change", args=[greenhouse.id])
                return format_html('<a href="{}">{}</a>', greenhouse_admin_url, greenhouse.name)
            except Exception:
                return greenhouse.name # Fallback
        return '-' # Display '-' if greenhouse is None
    clickable_greenhouse.short_description = 'Greenhouse' # Set the column header