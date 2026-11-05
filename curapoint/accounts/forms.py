from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import AuthenticationForm

from doctors.models import Doctor, Specialty

from .models import PatientProfile, User


class StyledFormMixin:
    """Adds the design-system CSS class to every widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            css = "form-select" if isinstance(widget, forms.Select) else "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()
            if field.required and not isinstance(widget, forms.Select):
                widget.attrs.setdefault("required", True)


class LoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.EmailField(label="Email address", widget=forms.EmailInput(attrs={"autofocus": True, "placeholder": "you@example.com", "autocomplete": "email"}))
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "current-password"}))
    remember_me = forms.BooleanField(required=False, initial=True, label="Remember me")

    def clean(self):
        email = self.cleaned_data.get("username")
        if email:
            self.cleaned_data["username"] = email.lower()
        return super().clean()


class SignUpForm(StyledFormMixin, forms.ModelForm):
    role = forms.ChoiceField(
        choices=[(User.Role.PATIENT, "I'm a patient"), (User.Role.DOCTOR, "I'm a doctor")],
        widget=forms.RadioSelect,
        initial=User.Role.PATIENT,
    )
    password1 = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "At least 8 characters"}))
    password2 = forms.CharField(label="Confirm password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Repeat password"}))
    specialty = forms.ModelChoiceField(queryset=Specialty.objects.all(), required=False, empty_label="Select your specialty")
    license_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={"placeholder": "Medical license number"}))
    accept_terms = forms.BooleanField(label="I agree to the Terms of Service and Privacy Policy")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "Jane"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Doe"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": "+1 555 000 0000"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords don't match.")
        if p1:
            candidate = User(email=cleaned.get("email", ""), first_name=cleaned.get("first_name", ""), last_name=cleaned.get("last_name", ""))
            try:
                password_validation.validate_password(p1, candidate)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        if cleaned.get("role") == User.Role.DOCTOR:
            if not cleaned.get("specialty"):
                self.add_error("specialty", "Please choose your specialty.")
            if not cleaned.get("license_number"):
                self.add_error("license_number", "A license number is required for doctors.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            if user.role == User.Role.DOCTOR:
                Doctor.objects.create(
                    user=user,
                    specialty=self.cleaned_data["specialty"],
                    license_number=self.cleaned_data["license_number"],
                    title=self.cleaned_data["specialty"].name,
                )
            else:
                PatientProfile.objects.create(user=user)
        return user


class UserProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "date_of_birth", "gender", "address", "avatar"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean_date_of_birth(self):
        from django.utils import timezone

        dob = self.cleaned_data.get("date_of_birth")
        if dob and dob > timezone.localdate():
            raise forms.ValidationError("Date of birth can't be in the future.")
        return dob


class PatientProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PatientProfile
        exclude = ["user"]
        widgets = {
            "allergies": forms.Textarea(attrs={"rows": 2}),
            "chronic_conditions": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_height_cm(self):
        h = self.cleaned_data.get("height_cm")
        if h is not None and not 40 <= h <= 260:
            raise forms.ValidationError("Enter a height between 40 and 260 cm.")
        return h

    def clean_weight_kg(self):
        w = self.cleaned_data.get("weight_kg")
        if w is not None and not 2 <= w <= 400:
            raise forms.ValidationError("Enter a weight between 2 and 400 kg.")
        return w


class DoctorProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Doctor
        fields = [
            "specialty", "title", "bio", "education", "languages", "license_number", "years_experience",
            "consultation_fee", "clinic_name", "location", "image", "offers_video", "is_accepting_patients",
        ]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4}), "education": forms.Textarea(attrs={"rows": 3})}
