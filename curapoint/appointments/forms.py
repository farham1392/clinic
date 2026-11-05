from datetime import timedelta

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.forms import StyledFormMixin

from .models import Appointment

MAX_BOOKING_DAYS = 60


class AppointmentBookingForm(StyledFormMixin, forms.ModelForm):
    time = forms.TimeField(widget=forms.HiddenInput, error_messages={"required": _("Please pick an available time slot.")})

    class Meta:
        model = Appointment
        fields = ["date", "time", "visit_type", "reason", "notes"]
        labels = {"date": _("Date"), "visit_type": _("Visit type"), "reason": _("Reason for visit"), "notes": _("Notes for the doctor")}
        help_texts = {"notes": ""}
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "visit_type": forms.RadioSelect,
            "reason": forms.TextInput(attrs={"placeholder": _("e.g. Annual check-up, chest pain, follow-up")}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": _("Symptoms, medications or anything the doctor should know (optional)")}),
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
            raise forms.ValidationError(_("You can't book an appointment in the past."))
        if day > today + timedelta(days=MAX_BOOKING_DAYS):
            raise forms.ValidationError(_("Appointments can be booked up to %(days)s days ahead.") % {"days": MAX_BOOKING_DAYS})
        if day.weekday() not in self.doctor.working_days():
            raise forms.ValidationError(_("%(doctor)s doesn't see patients on this day of the week.") % {"doctor": self.doctor})
        return day

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if len(reason) < 3:
            raise forms.ValidationError(_("Please describe the reason for your visit."))
        return reason

    def clean(self):
        cleaned = super().clean()
        day, time = cleaned.get("date"), cleaned.get("time")
        if not self.doctor.is_accepting_patients:
            raise forms.ValidationError(_("%(doctor)s is not accepting new appointments right now.") % {"doctor": self.doctor})
        if day and time:
            if time not in self.doctor.slots_for(day):
                self.add_error("time", _("That time slot is no longer available. Please choose another."))
            elif Appointment.objects.filter(patient=self.patient, date=day, time=time).exclude(status=Appointment.Status.CANCELLED).exists():
                self.add_error("time", _("You already have another appointment at this time."))
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
        labels = {"status": _("Status"), "doctor_notes": _("Clinical notes")}
        help_texts = {"doctor_notes": ""}
        widgets = {"doctor_notes": forms.Textarea(attrs={"rows": 4, "placeholder": _("Clinical notes (visible to you only)")})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = self.instance.status
        allowed = [current] + list(self.ALLOWED_TRANSITIONS.get(current, []))
        self.fields["status"].choices = [(s, Appointment.Status(s).label) for s in allowed]

    def clean_status(self):
        new = self.cleaned_data["status"]
        current = self.instance.status
        if new != current and new not in self.ALLOWED_TRANSITIONS.get(current, []):
            raise forms.ValidationError(_("Can't change a %(current)s appointment to %(new)s.") % {"current": Appointment.Status(current).label, "new": Appointment.Status(new).label})
        return new


class CancelAppointmentForm(forms.Form):
    confirm = forms.BooleanField(required=True)
