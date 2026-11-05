from datetime import datetime

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class AppointmentQuerySet(models.QuerySet):
    def upcoming(self):
        today = timezone.localdate()
        return self.filter(date__gte=today, status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED])

    def past(self):
        today = timezone.localdate()
        return self.filter(models.Q(date__lt=today) | models.Q(status__in=[Appointment.Status.COMPLETED, Appointment.Status.CANCELLED]))


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    class VisitType(models.TextChoices):
        IN_PERSON = "in_person", "In-person visit"
        VIDEO = "video", "Video consultation"

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE, related_name="appointments")
    date = models.DateField(db_index=True)
    time = models.TimeField()
    visit_type = models.CharField(max_length=12, choices=VisitType.choices, default=VisitType.IN_PERSON)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    reason = models.CharField(max_length=255)
    notes = models.TextField(blank=True, help_text="Notes from the patient")
    doctor_notes = models.TextField(blank=True, help_text="Private clinical notes from the doctor")
    fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AppointmentQuerySet.as_manager()

    class Meta:
        ordering = ["date", "time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "date", "time"],
                condition=~models.Q(status="cancelled"),
                name="unique_active_doctor_slot",
            )
        ]

    def __str__(self):
        return f"{self.patient} with {self.doctor} on {self.date} {self.time:%H:%M}"

    def get_absolute_url(self):
        return reverse("appointments:detail", kwargs={"pk": self.pk})

    @property
    def starts_at(self):
        return timezone.make_aware(datetime.combine(self.date, self.time)) if settings.USE_TZ else datetime.combine(self.date, self.time)

    @property
    def is_upcoming(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED) and self.starts_at >= timezone.now()

    @property
    def can_cancel(self):
        return self.is_upcoming

    @property
    def status_color(self):
        return {
            self.Status.PENDING: "warning",
            self.Status.CONFIRMED: "primary",
            self.Status.COMPLETED: "success",
            self.Status.CANCELLED: "danger",
            self.Status.NO_SHOW: "muted",
        }.get(self.status, "muted")
