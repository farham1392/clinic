from django.db.models import Count
from django.shortcuts import render

from doctors.models import Doctor, Specialty
from appointments.models import Appointment


def home(request):
    specialties = Specialty.objects.annotate(doctor_count=Count("doctors")).order_by("-doctor_count", "name")[:8]
    featured = Doctor.objects.active().select_related("user", "specialty").filter(is_featured=True)[:4]
    if not featured:
        featured = Doctor.objects.active().select_related("user", "specialty")[:4]
    stats = {
        "doctors": Doctor.objects.active().count(),
        "specialties": Specialty.objects.count(),
        "appointments": Appointment.objects.count(),
    }
    return render(
        request,
        "core/home.html",
        {"specialties": specialties, "featured_doctors": featured, "stats": stats, "all_specialties": Specialty.objects.all()},
    )


def about(request):
    return render(request, "core/about.html")


def handler404(request, exception):
    return render(request, "errors/404.html", status=404)


def handler500(request):
    return render(request, "errors/500.html", status=500)
