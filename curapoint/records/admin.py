from django.contrib import admin

from .models import HealthMetric, MedicalRecord


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ["title", "record_type", "patient", "doctor", "record_date"]
    list_filter = ["record_type", "record_date"]
    search_fields = ["title", "patient__email", "patient__last_name"]


@admin.register(HealthMetric)
class HealthMetricAdmin(admin.ModelAdmin):
    list_display = ["patient", "metric_type", "display_value", "unit", "recorded_at"]
    list_filter = ["metric_type"]
