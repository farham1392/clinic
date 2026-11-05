from django.urls import path

from . import views

app_name = "doctors"
urlpatterns = [
    path("", views.doctor_list, name="list"),
    path("availability/", views.manage_availability, name="availability"),
    path("<slug:slug>/", views.doctor_detail, name="detail"),
    path("<slug:slug>/slots/", views.doctor_slots, name="slots"),
    path("<slug:slug>/review/", views.add_review, name="review"),
]
