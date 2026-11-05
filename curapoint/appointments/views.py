from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from core.decorators import doctor_required, patient_required
from doctors.models import Doctor

from .forms import AppointmentBookingForm, AppointmentStatusForm
from .models import Appointment


def _get_for_user(user, pk):
    appt = get_object_or_404(Appointment.objects.select_related("doctor__user", "doctor__specialty", "patient"), pk=pk)
    if user.is_staff or appt.patient_id == user.id or (user.is_doctor and appt.doctor.user_id == user.id):
        return appt
    raise Http404


@patient_required
@require_http_methods(["GET", "POST"])
def book(request, slug):
    doctor = get_object_or_404(Doctor.objects.select_related("user", "specialty"), slug=slug, user__is_active=True)
    initial = {}
    if request.GET.get("date"):
        initial["date"] = request.GET["date"]
    elif (first_slot := doctor.next_available()) is not None:
        initial["date"] = first_slot.date()
    form = AppointmentBookingForm(request.POST or None, doctor=doctor, patient=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                appt = form.save()
        except IntegrityError:
            form.add_error("time", "Sorry, that slot was just taken. Please pick another time.")
        else:
            messages.success(request, f"Appointment requested with {doctor} on {appt.date:%b %d} at {appt.time:%I:%M %p}.")
            return redirect("appointments:detail", pk=appt.pk)
    return render(request, "appointments/book.html", {"doctor": doctor, "form": form})


@login_required
def appointment_list(request):
    user = request.user
    if user.is_doctor and hasattr(user, "doctor_profile"):
        qs = Appointment.objects.filter(doctor=user.doctor_profile).select_related("patient")
    else:
        qs = Appointment.objects.filter(patient=user).select_related("doctor__user", "doctor__specialty")
    tab = request.GET.get("tab", "upcoming")
    status = request.GET.get("status")
    if tab == "past":
        qs = qs.past().order_by("-date", "-time")
    elif tab == "all":
        qs = qs.order_by("-date", "-time")
    else:
        tab = "upcoming"
        qs = qs.upcoming()
    if status in Appointment.Status.values:
        qs = qs.filter(status=status)
    return render(request, "appointments/appointment_list.html", {"appointments": qs, "tab": tab, "status": status, "statuses": Appointment.Status.choices})


@login_required
def appointment_detail(request, pk):
    appt = _get_for_user(request.user, pk)
    status_form = None
    if request.user.is_doctor and appt.doctor.user_id == request.user.id:
        status_form = AppointmentStatusForm(instance=appt)
    return render(request, "appointments/appointment_detail.html", {"appointment": appt, "status_form": status_form, "records": appt.records.all()})


@login_required
@require_POST
def cancel(request, pk):
    appt = _get_for_user(request.user, pk)
    if not appt.can_cancel:
        messages.error(request, "This appointment can no longer be cancelled.")
    else:
        appt.status = Appointment.Status.CANCELLED
        appt.save(update_fields=["status", "updated_at"])
        messages.success(request, "Appointment cancelled.")
    return redirect(request.POST.get("next") or appt.get_absolute_url())


@doctor_required
@require_POST
def update_status(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, doctor=request.user.doctor_profile)
    form = AppointmentStatusForm(request.POST, instance=appt)
    if form.is_valid():
        form.save()
        messages.success(request, f"Appointment marked as {appt.get_status_display().lower()}.")
    else:
        for errors in form.errors.values():
            for e in errors:
                messages.error(request, e)
    return redirect(request.POST.get("next") or appt.get_absolute_url())


@doctor_required
@require_POST
def quick_action(request, pk, action):
    appt = get_object_or_404(Appointment, pk=pk, doctor=request.user.doctor_profile)
    target = {"confirm": Appointment.Status.CONFIRMED, "complete": Appointment.Status.COMPLETED, "decline": Appointment.Status.CANCELLED}.get(action)
    if target is None:
        raise Http404
    form = AppointmentStatusForm({"status": target, "doctor_notes": appt.doctor_notes}, instance=appt)
    if form.is_valid():
        form.save()
        messages.success(request, f"Appointment with {appt.patient} {appt.get_status_display().lower()}.")
    else:
        messages.error(request, "That action isn't allowed for this appointment.")
    return redirect(request.POST.get("next") or "dashboard:doctor")
