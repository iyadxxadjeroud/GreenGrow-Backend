# dashboard/filters.py
from django.contrib import admin

class ValueRangeFilter(admin.SimpleListFilter):
    title = 'Plage de Valeurs'
    parameter_name = 'value_range'

    def lookups(self, request, model_admin):
        return [
            ('low', 'Faible (< 50)'),
            ('medium', 'Moyenne (50-100)'),
            ('high', 'Élevée (> 100)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(value__lt=50)
        if self.value() == 'medium':
            return queryset.filter(value__range=(50, 100))
        if self.value() == 'high':
            return queryset.filter(value__gt=100)