from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from accounts.forms import StyledFormMixin

from .models import Availability, Doctor, Review, Specialty


class DoctorSearchForm(forms.Form):
    SORT_CHOICES = [
        ("recommended", _("Recommended")),
        ("rating", _("Highest rated")),
        ("experience", _("Most experienced")),
        ("fee_low", _("Fee: low to high")),
        ("fee_high", _("Fee: high to low")),
    ]
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": _("Search doctors, specialties, clinics…"), "class": "form-control"}))
    specialty = forms.ModelChoiceField(queryset=Specialty.objects.all(), required=False, to_field_name="slug", empty_label=_("All specialties"), widget=forms.Select(attrs={"class": "form-select"}))
    location = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": _("City or area"), "class": "form-control"}))
    video = forms.BooleanField(required=False, label=_("Video consultation"))
    accepting = forms.BooleanField(required=False, label=_("Accepting new patients"))
    min_rating = forms.TypedChoiceField(
        required=False, coerce=float, empty_value=None,
        choices=[("", _("Any rating")), ("4.5", "4.5+"), ("4", "4.0+"), ("3", "3.0+")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))


class ReviewForm(StyledFormMixin, forms.ModelForm):
    rating = forms.TypedChoiceField(coerce=int, choices=[(i, ngettext_lazy("%(n)d star", "%(n)d stars", i) % {"n": i}) for i in range(5, 0, -1)], widget=forms.RadioSelect)

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        labels = {"comment": _("Comment")}
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "placeholder": _("Share your experience (optional)")})}


class AvailabilityForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Availability
        fields = ["weekday", "start_time", "end_time", "slot_minutes", "is_active"]
        labels = {"weekday": _("Day"), "start_time": _("Start time"), "end_time": _("End time"), "slot_minutes": _("Slot (minutes)"), "is_active": _("Active")}
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", _("End time must be after start time."))
        return cleaned


class BaseAvailabilityFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        windows = []
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            d = form.cleaned_data
            if d.get("weekday") is None or not d.get("start_time") or not d.get("end_time"):
                continue
            for other in windows:
                if other["weekday"] == d["weekday"] and d["start_time"] < other["end_time"] and other["start_time"] < d["end_time"]:
                    raise forms.ValidationError(
                        _("Overlapping hours on %(day)s. Please merge or adjust them.") % {"day": Availability.Weekday(d["weekday"]).label}
                    )
            windows.append(d)


AvailabilityFormSet = inlineformset_factory(
    Doctor, Availability, form=AvailabilityForm, formset=BaseAvailabilityFormSet, extra=1, can_delete=True
)
