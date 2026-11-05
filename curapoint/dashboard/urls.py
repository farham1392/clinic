from django.urls import path

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.home, name="home"),
    path("patient/", views.patient_dashboard, name="patient"),
    path("doctor/", views.doctor_dashboard, name="doctor"),
    path("doctor/patients/", views.doctor_patients, name="patients"),
    path("doctor/patients/<int:pk>/", views.doctor_patient_detail, name="patient_detail"),
]
