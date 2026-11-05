from datetime import date as date_cls, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from django.utils.translation import get_language_bidi, gettext as _
from django.utils.formats import time_format

from appointments.models import Appointment
from core.decorators import doctor_required, patient_required

from .forms import AvailabilityFormSet, DoctorSearchForm, ReviewForm
from .models import Doctor, Review


def doctor_list(request):
    form = DoctorSearchForm(request.GET or None)
    doctors = Doctor.objects.active().select_related("user", "specialty")
    if form.is_valid():
        d = form.cleaned_data
        if d.get("q"):
            q = d["q"]
            doctors = doctors.filter(
                Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(specialty__name__icontains=q)
                | Q(title__icontains=q) | Q(clinic_name__icontains=q) | Q(bio__icontains=q)
            )
        if d.get("specialty"):
            doctors = doctors.filter(specialty=d["specialty"])
        if d.get("location"):
            doctors = doctors.filter(location__icontains=d["location"])
        if d.get("video"):
            doctors = doctors.filter(offers_video=True)
        if d.get("accepting"):
            doctors = doctors.filter(is_accepting_patients=True)
        if d.get("min_rating"):
            doctors = doctors.filter(rating__gte=d["min_rating"])
        ordering = {
            "rating": ["-rating", "-review_count"],
            "experience": ["-years_experience"],
            "fee_low": ["consultation_fee"],
            "fee_high": ["-consultation_fee"],
        }.get(d.get("sort"))
        if ordering:
            doctors = doctors.order_by(*ordering)
    page = Paginator(doctors, 9).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "doctors/doctor_list.html", {"form": form, "page_obj": page, "doctors": page.object_list, "querystring": params.urlencode()})


def doctor_detail(request, slug):
    doctor = get_object_or_404(Doctor.objects.select_related("user", "specialty"), slug=slug, user__is_active=True)
    today = timezone.localdate()
    days = []
    for offset in range(14):
        day = today + timedelta(days=offset)
        slots = doctor.slots_for(day)
        days.append({"date": day, "count": len(slots)})
    reviews = doctor.reviews.select_related("patient")[:10]
    can_review = False
    if request.user.is_authenticated and request.user.is_patient:
        can_review = Appointment.objects.filter(
            doctor=doctor, patient=request.user, status=Appointment.Status.COMPLETED, review__isnull=True
        ).exists()
    related = Doctor.objects.active().filter(specialty=doctor.specialty).exclude(pk=doctor.pk).select_related("user", "specialty")[:3]
    return render(request, "doctors/doctor_detail.html", {
        "doctor": doctor,
        "days": days,
        "reviews": reviews,
        "can_review": can_review,
        "review_form": ReviewForm() if can_review else None,
        "related_doctors": related,
        "availability": doctor.availability.filter(is_active=True),
    })


@require_GET
def doctor_slots(request, slug):
    doctor = get_object_or_404(Doctor, slug=slug)
    try:
        day = date_cls.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return JsonResponse({"error": _("Invalid date. Use YYYY-MM-DD.")}, status=400)
    slots = doctor.slots_for(day) if day >= timezone.localdate() else []
    return JsonResponse({"date": day.isoformat(), "slots": [{"value": s.strftime("%H:%M"), "label": time_format(s, "H:i" if get_language_bidi() else "g:i A")} for s in slots]})


@patient_required
@require_http_methods(["POST"])
def add_review(request, slug):
    doctor = get_object_or_404(Doctor, slug=slug)
    appointment = Appointment.objects.filter(
        doctor=doctor, patient=request.user, status=Appointment.Status.COMPLETED, review__isnull=True
    ).order_by("-date").first()
    if appointment is None:
        messages.error(request, _("You can review a doctor after a completed appointment."))
        return redirect(doctor)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.doctor, review.patient, review.appointment = doctor, request.user, appointment
        review.save()
        doctor.refresh_rating()
        messages.success(request, _("Thanks for your feedback!"))
    else:
        messages.error(request, _("Please choose a rating between 1 and 5."))
    return redirect(doctor)


@doctor_required
@require_http_methods(["GET", "POST"])
def manage_availability(request):
    doctor = request.user.doctor_profile
    formset = AvailabilityFormSet(request.POST or None, instance=doctor)
    if request.method == "POST":
        if formset.is_valid():
            formset.save()
            messages.success(request, _("Availability updated."))
            return redirect("doctors:availability")
        messages.error(request, _("Please fix the errors below."))
    return render(request, "doctors/availability.html", {"formset": formset})
