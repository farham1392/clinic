from datetime import timedelta

from django import forms
from django.utils import timezone

from accounts.forms import StyledFormMixin

from .models import Appointment

MAX_BOOKING_DAYS = 60


class AppointmentBookingForm(StyledFormMixin, forms.ModelForm):
    time = forms.TimeField(widget=forms.HiddenInput, error_messages={"required": "Please pick an available time slot."})

    class Meta:
        model = Appointment
        fields = ["date", "time", "visit_type", "reason", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "visit_type": forms.RadioSelect,
            "reason": forms.TextInput(attrs={"placeholder": "e.g. Annual check-up, chest pain, follow-up"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Symptoms, medications or anything the doctor should know (optional)"}),
        }

    def __init__(self, *args, doctor, patient, **kwargs):
        self.doctor, self.patient = doctor, patient
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["date"].widget.attrs.update({"min": today.isoformat(), "max": (today + timedelta(days=MAX_BOOKING_DAYS)).isoformat()})
        if not doctor.offers_video:
            self.fields["visit_type"].choices = [(Appointment.VisitType.IN_PERSON, Appointment.VisitType.IN_PERSON.label)]

    def clean_date(self):
        day = self.cleaned_data["date"]
        today = timezone.localdate()
        if day < today:
            raise forms.ValidationError("You can't book an appointment in the past.")
        if day > today + timedelta(days=MAX_BOOKING_DAYS):
            raise forms.ValidationError(f"Appointments can be booked up to {MAX_BOOKING_DAYS} days ahead.")
        if day.weekday() not in self.doctor.working_days():
            raise forms.ValidationError(f"{self.doctor} doesn't see patients on {day:%A}s.")
        return day

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if len(reason) < 3:
            raise forms.ValidationError("Please describe the reason for your visit.")
        return reason

    def clean(self):
        cleaned = super().clean()
        day, time = cleaned.get("date"), cleaned.get("time")
        if not self.doctor.is_accepting_patients:
            raise forms.ValidationError(f"{self.doctor} is not accepting new appointments right now.")
        if day and time:
            if time not in self.doctor.slots_for(day):
                self.add_error("time", "That time slot is no longer available. Please choose another.")
            elif Appointment.objects.filter(patient=self.patient, date=day, time=time).exclude(status=Appointment.Status.CANCELLED).exists():
                self.add_error("time", "You already have another appointment at this time.")
        return cleaned

    def save(self, commit=True):
        appt = super().save(commit=False)
        appt.doctor, appt.patient = self.doctor, self.patient
        appt.fee = self.doctor.consultation_fee
        if commit:
            appt.save()
        return appt


class AppointmentStatusForm(StyledFormMixin, forms.ModelForm):
    ALLOWED_TRANSITIONS = {
        Appointment.Status.PENDING: [Appointment.Status.CONFIRMED, Appointment.Status.CANCELLED],
        Appointment.Status.CONFIRMED: [Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW],
    }

    class Meta:
        model = Appointment
        fields = ["status", "doctor_notes"]
        widgets = {"doctor_notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Clinical notes (visible to you only)"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = self.instance.status
        allowed = [current] + list(self.ALLOWED_TRANSITIONS.get(current, []))
        self.fields["status"].choices = [(s, Appointment.Status(s).label) for s in allowed]

    def clean_status(self):
        new = self.cleaned_data["status"]
        current = self.instance.status
        if new != current and new not in self.ALLOWED_TRANSITIONS.get(current, []):
            raise forms.ValidationError(f"Can't change a {current} appointment to {new}.")
        return new


class CancelAppointmentForm(forms.Form):
    confirm = forms.BooleanField(required=True)
