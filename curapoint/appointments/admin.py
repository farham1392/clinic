from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["patient", "doctor", "date", "time", "visit_type", "status", "fee"]
    list_filter = ["status", "visit_type", "date", "doctor__specialty"]
    search_fields = ["patient__email", "patient__first_name", "patient__last_name", "doctor__user__last_name", "reason"]
    date_hierarchy = "date"
    autocomplete_fields = ["patient"]
    list_select_related = ["patient", "doctor__user"]
