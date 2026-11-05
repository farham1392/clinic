from django.conf import settings
from django.db import models


class MedicalRecord(models.Model):
    class RecordType(models.TextChoices):
        DIAGNOSIS = "diagnosis", "Diagnosis"
        PRESCRIPTION = "prescription", "Prescription"
        LAB_RESULT = "lab_result", "Lab result"
        VACCINATION = "vaccination", "Vaccination"
        IMAGING = "imaging", "Imaging"
        NOTE = "note", "Clinical note"

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medical_records")
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.SET_NULL, null=True, blank=True, related_name="records")
    appointment = models.ForeignKey(
        "appointments.Appointment", on_delete=models.SET_NULL, null=True, blank=True, related_name="records"
    )
    record_type = models.CharField(max_length=15, choices=RecordType.choices, default=RecordType.NOTE)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    record_date = models.DateField()
    attachment = models.FileField(upload_to="records/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-record_date", "-created_at"]

    def __str__(self):
        return f"{self.get_record_type_display()}: {self.title} ({self.patient})"

    @property
    def icon(self):
        return {
            "diagnosis": "fa-notes-medical",
            "prescription": "fa-prescription-bottle-medical",
            "lab_result": "fa-flask-vial",
            "vaccination": "fa-syringe",
            "imaging": "fa-x-ray",
        }.get(self.record_type, "fa-file-medical")


class HealthMetric(models.Model):
    class MetricType(models.TextChoices):
        HEART_RATE = "heart_rate", "Heart rate"
        BLOOD_PRESSURE = "blood_pressure", "Blood pressure"
        GLUCOSE = "glucose", "Blood glucose"
        WEIGHT = "weight", "Weight"
        TEMPERATURE = "temperature", "Body temperature"
        OXYGEN = "oxygen", "Oxygen saturation"

    UNITS = {
        "heart_rate": "bpm",
        "blood_pressure": "mmHg",
        "glucose": "mg/dL",
        "weight": "kg",
        "temperature": "°C",
        "oxygen": "%",
    }
    ICONS = {
        "heart_rate": "fa-heart-pulse",
        "blood_pressure": "fa-gauge-high",
        "glucose": "fa-droplet",
        "weight": "fa-weight-scale",
        "temperature": "fa-temperature-half",
        "oxygen": "fa-lungs",
    }

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="health_metrics")
    metric_type = models.CharField(max_length=15, choices=MetricType.choices)
    value = models.DecimalField(max_digits=6, decimal_places=1)
    value_secondary = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True, help_text="Diastolic value for blood pressure"
    )
    recorded_at = models.DateTimeField()
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["patient", "metric_type", "-recorded_at"])]

    def __str__(self):
        return f"{self.get_metric_type_display()} {self.display_value} ({self.patient})"

    @property
    def unit(self):
        return self.UNITS.get(self.metric_type, "")

    @property
    def icon(self):
        return self.ICONS.get(self.metric_type, "fa-chart-line")

    @property
    def display_value(self):
        def fmt(v):
            return f"{v:.0f}" if v == int(v) else f"{v}"

        if self.metric_type == self.MetricType.BLOOD_PRESSURE and self.value_secondary is not None:
            return f"{fmt(self.value)}/{fmt(self.value_secondary)}"
        return fmt(self.value)
