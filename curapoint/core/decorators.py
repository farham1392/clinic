from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    """Restrict a view to authenticated users having one of the given roles."""

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, "You don't have access to that page.")
                return redirect("dashboard:home")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def patient_required(view):
    return role_required("patient")(view)


def doctor_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "doctor_profile"):
            messages.error(request, "Your doctor profile is not set up yet.")
            return redirect("core:home")
        return view(request, *args, **kwargs)

    return role_required("doctor")(wrapper)
