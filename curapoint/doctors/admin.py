from django.contrib import admin

from .models import Availability, Doctor, Review, Specialty


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon"]
    prepopulated_fields = {"slug": ["name"]}
    search_fields = ["name"]


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ["__str__", "specialty", "rating", "review_count", "years_experience", "consultation_fee", "is_accepting_patients", "is_featured"]
    list_filter = ["specialty", "is_accepting_patients", "is_featured", "offers_video"]
    list_editable = ["is_featured", "is_accepting_patients"]
    search_fields = ["user__first_name", "user__last_name", "user__email", "clinic_name"]
    autocomplete_fields = ["user"]
    inlines = [AvailabilityInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["doctor", "patient", "rating", "created_at"]
    list_filter = ["rating"]
