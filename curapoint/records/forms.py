from django import forms
from django.utils import timezone

from accounts.forms import StyledFormMixin

from .models import HealthMetric, MedicalRecord

METRIC_RANGES = {
    "heart_rate": (20, 250),
    "blood_pressure": (50, 260),
    "glucose": (20, 600),
    "weight": (2, 400),
    "temperature": (30, 45),
    "oxygen": (50, 100),
}


class MedicalRecordForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ["record_type", "title", "description", "record_date", "attachment"]
        widgets = {
            "record_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_record_date(self):
        d = self.cleaned_data["record_date"]
        if d > timezone.localdate():
            raise forms.ValidationError("Record date can't be in the future.")
        return d

    def clean_attachment(self):
        f = self.cleaned_data.get("attachment")
        if f and hasattr(f, "size") and f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Attachments must be 10 MB or smaller.")
        return f


class HealthMetricForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = HealthMetric
        fields = ["metric_type", "value", "value_secondary", "recorded_at", "note"]
        widgets = {"recorded_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")}
        labels = {"value": "Value", "value_secondary": "Diastolic (BP only)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get("recorded_at"):
            self.initial["recorded_at"] = timezone.localtime().strftime("%Y-%m-%dT%H:%M")

    def clean_recorded_at(self):
        value = self.cleaned_data["recorded_at"]
        if value > timezone.now() + timezone.timedelta(minutes=5):
            raise forms.ValidationError("Readings can't be recorded in the future.")
        return value

    def clean(self):
        cleaned = super().clean()
        mtype, value, secondary = cleaned.get("metric_type"), cleaned.get("value"), cleaned.get("value_secondary")
        if mtype and value is not None:
            lo, hi = METRIC_RANGES[mtype]
            if not lo <= value <= hi:
                self.add_error("value", f"Value should be between {lo} and {hi}.")
        if mtype == HealthMetric.MetricType.BLOOD_PRESSURE:
            if secondary is None:
                self.add_error("value_secondary", "Enter the diastolic value for blood pressure.")
            elif value is not None and secondary >= value:
                self.add_error("value_secondary", "Diastolic must be lower than systolic.")
        elif secondary is not None:
            cleaned["value_secondary"] = None
        return cleaned
