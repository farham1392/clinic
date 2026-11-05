from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import User
from appointments.models import Appointment
from core.decorators import doctor_required, patient_required
from records.forms import MedicalRecordForm
from records.models import HealthMetric, MedicalRecord


@login_required
def home(request):
    user = request.user
    if user.is_doctor:
        return redirect("dashboard:doctor")
    if user.is_patient:
        return redirect("dashboard:patient")
    return redirect("admin:index")


def _latest_metrics(patient):
    latest = []
    for mtype, label in HealthMetric.MetricType.choices:
        readings = list(HealthMetric.objects.filter(patient=patient, metric_type=mtype).order_by("-recorded_at")[:7])
        if readings:
            series = [float(r.value) for r in reversed(readings)]
            hi, lo = max(series), min(series)
            spread = (hi - lo) or 1
            points = " ".join(f"{i * (100 / max(len(series) - 1, 1)):.1f},{30 - (v - lo) / spread * 26 - 2:.1f}" for i, v in enumerate(series))
            trend = series[-1] - series[0] if len(series) > 1 else 0
            latest.append({"type": mtype, "label": label, "reading": readings[0], "points": points, "trend": trend})
    return latest


@patient_required
def patient_dashboard(request):
    user = request.user
    appts = Appointment.objects.filter(patient=user).select_related("doctor__user", "doctor__specialty")
    upcoming = appts.upcoming()
    stats = appts.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
        upcoming=Count("id", filter=Q(status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED], date__gte=timezone.localdate())),
        doctors=Count("doctor", distinct=True),
    )
    context = {
        "next_appointment": upcoming.first(),
        "upcoming": upcoming[:5],
        "recent": appts.past().order_by("-date", "-time")[:4],
        "stats": stats,
        "metrics": _latest_metrics(user),
        "records": MedicalRecord.objects.filter(patient=user).select_related("doctor__user")[:5],
        "profile": getattr(user, "patient_profile", None),
    }
    return render(request, "dashboard/patient.html", context)


@doctor_required
def doctor_dashboard(request):
    doctor = request.user.doctor_profile
    today = timezone.localdate()
    appts = Appointment.objects.filter(doctor=doctor).select_related("patient")
    week_start = today - timedelta(days=today.weekday())
    stats = appts.aggregate(
        today=Count("id", filter=Q(date=today) & ~Q(status=Appointment.Status.CANCELLED)),
        pending=Count("id", filter=Q(status=Appointment.Status.PENDING, date__gte=today)),
        week=Count("id", filter=Q(date__gte=week_start, date__lt=week_start + timedelta(days=7)) & ~Q(status=Appointment.Status.CANCELLED)),
        patients=Count("patient", distinct=True),
        completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
        revenue=Sum("fee", filter=Q(status=Appointment.Status.COMPLETED)),
    )
    week = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        week.append({"date": day, "count": appts.filter(date=day).exclude(status=Appointment.Status.CANCELLED).count(), "is_today": day == today})
    max_week = max([d["count"] for d in week] + [1])
    context = {
        "doctor": doctor,
        "stats": stats,
        "today_schedule": appts.filter(date=today).exclude(status=Appointment.Status.CANCELLED).order_by("time"),
        "pending_requests": appts.filter(status=Appointment.Status.PENDING, date__gte=today).order_by("date", "time")[:6],
        "upcoming": appts.filter(status=Appointment.Status.CONFIRMED, date__gt=today).order_by("date", "time")[:6],
        "week": week,
        "max_week": max_week,
        "recent_reviews": doctor.reviews.select_related("patient")[:3],
    }
    return render(request, "dashboard/doctor.html", context)


@doctor_required
def doctor_patients(request):
    doctor = request.user.doctor_profile
    q = request.GET.get("q", "").strip()
    patients = (
        User.objects.filter(appointments__doctor=doctor)
        .annotate(
            visit_count=Count("appointments", filter=Q(appointments__doctor=doctor)),
            last_visit=Max("appointments__date", filter=Q(appointments__doctor=doctor)),
        )
        .distinct()
        .order_by("-last_visit")
    )
    if q:
        patients = patients.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    return render(request, "dashboard/doctor_patients.html", {"patients": patients, "q": q})


@doctor_required
@require_http_methods(["GET", "POST"])
def doctor_patient_detail(request, pk):
    doctor = request.user.doctor_profile
    patient = get_object_or_404(User, pk=pk, role=User.Role.PATIENT)
    if not Appointment.objects.filter(doctor=doctor, patient=patient).exists():
        raise Http404
    form = MedicalRecordForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            record = form.save(commit=False)
            record.patient, record.doctor = patient, doctor
            record.save()
            messages.success(request, "Medical record added.")
            return redirect("dashboard:patient_detail", pk=patient.pk)
        messages.error(request, "Please correct the errors in the record form.")
    context = {
        "patient": patient,
        "profile": getattr(patient, "patient_profile", None),
        "appointments": Appointment.objects.filter(doctor=doctor, patient=patient).order_by("-date", "-time"),
        "records": MedicalRecord.objects.filter(patient=patient).select_related("doctor__user"),
        "metrics": _latest_metrics(patient),
        "form": form,
    }
    return render(request, "dashboard/doctor_patient_detail.html", context)
