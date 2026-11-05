from django.urls import path

from . import views

app_name = "appointments"
urlpatterns = [
    path("", views.appointment_list, name="list"),
    path("book/<slug:slug>/", views.book, name="book"),
    path("<int:pk>/", views.appointment_detail, name="detail"),
    path("<int:pk>/cancel/", views.cancel, name="cancel"),
    path("<int:pk>/status/", views.update_status, name="status"),
    path("<int:pk>/<str:action>/", views.quick_action, name="quick_action"),
]
