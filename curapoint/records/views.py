from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _

from core.decorators import patient_required

from .forms import HealthMetricForm
from .models import HealthMetric, MedicalRecord


@patient_required
def record_list(request):
    records = MedicalRecord.objects.filter(patient=request.user).select_related("doctor__user")
    rtype = request.GET.get("type")
    if rtype in MedicalRecord.RecordType.values:
        records = records.filter(record_type=rtype)
    return render(request, "records/record_list.html", {"records": records, "types": MedicalRecord.RecordType.choices, "current_type": rtype})


@patient_required
@require_http_methods(["GET", "POST"])
def metrics(request):
    form = HealthMetricForm(request.POST or None, initial={"metric_type": request.GET.get("type")})
    if request.method == "POST":
        if form.is_valid():
            metric = form.save(commit=False)
            metric.patient = request.user
            metric.save()
            messages.success(request, _("%(metric)s reading saved.") % {"metric": metric.get_metric_type_display()})
            return redirect("records:metrics")
        messages.error(request, _("Please correct the errors below."))
    readings = HealthMetric.objects.filter(patient=request.user)[:50]
    return render(request, "records/metrics.html", {"form": form, "readings": readings})
