from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import DoctorProfileForm, LoginForm, PatientProfileForm, SignUpForm, UserProfileForm
from .models import PatientProfile


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)
        messages.success(self.request, f"Welcome back, {form.get_user().first_name or 'there'}!")
        return super().form_valid(form)


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    initial = {"role": request.GET.get("role", "patient")}
    form = SignUpForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Your CuraPoint account has been created.")
        if user.is_doctor:
            messages.info(request, "Complete your profile and set your availability so patients can book you.")
            return redirect("accounts:profile")
        return redirect("dashboard:home")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    user = request.user
    user_form = UserProfileForm(request.POST or None, request.FILES or None, instance=user, prefix="user")
    extra_form = None
    if user.is_doctor and hasattr(user, "doctor_profile"):
        extra_form = DoctorProfileForm(request.POST or None, request.FILES or None, instance=user.doctor_profile, prefix="doc")
    elif user.is_patient:
        patient_profile, _ = PatientProfile.objects.get_or_create(user=user)
        extra_form = PatientProfileForm(request.POST or None, instance=patient_profile, prefix="pat")
    if request.method == "POST":
        forms_ok = user_form.is_valid() and (extra_form is None or extra_form.is_valid())
        if forms_ok:
            user_form.save()
            if extra_form is not None:
                extra_form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
        messages.error(request, "Please correct the errors below.")
    return render(request, "accounts/profile.html", {"user_form": user_form, "extra_form": extra_form})
