from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment
from doctors.models import Availability, Doctor, Specialty
from records.models import HealthMetric

PASSWORD = "Str0ng!Pass99"


def next_weekday(weekday):
    day = timezone.localdate() + timedelta(days=1)
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return day


class CuraPointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.spec = Specialty.objects.create(name="Cardiology", icon="fa-heart-pulse")
        cls.doc_user = User.objects.create_user("doc@test.com", PASSWORD, first_name="Gregory", last_name="House", role=User.Role.DOCTOR)
        cls.doctor = Doctor.objects.create(user=cls.doc_user, specialty=cls.spec, consultation_fee=100, license_number="MD-1")
        Availability.objects.create(doctor=cls.doctor, weekday=0, start_time=time(9), end_time=time(11), slot_minutes=30)
        cls.patient = User.objects.create_user("pat@test.com", PASSWORD, first_name="Pat", last_name="Smith", role=User.Role.PATIENT)
        cls.other = User.objects.create_user("other@test.com", PASSWORD, first_name="Oli", last_name="Ver", role=User.Role.PATIENT)
        cls.monday = next_weekday(0)

    def book(self, user, **overrides):
        self.client.force_login(user)
        data = {"date": self.monday.isoformat(), "time": "09:30", "visit_type": "in_person", "reason": "Routine heart check", "notes": ""}
        data.update(overrides)
        return self.client.post(reverse("appointments:book", args=[self.doctor.slug]), data)

    def test_public_pages(self):
        for name, args in [("core:home", []), ("core:about", []), ("doctors:list", []), ("doctors:detail", [self.doctor.slug]), ("accounts:login", []), ("accounts:signup", [])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)

    def test_doctor_search_filters(self):
        r = self.client.get(reverse("doctors:list"), {"q": "house", "specialty": self.spec.slug})
        self.assertContains(r, "Gregory House")
        r = self.client.get(reverse("doctors:list"), {"q": "nobody"})
        self.assertNotContains(r, "Gregory House")

    def test_slots_endpoint(self):
        r = self.client.get(reverse("doctors:slots", args=[self.doctor.slug]), {"date": self.monday.isoformat()})
        self.assertEqual(r.status_code, 200)
        self.assertIn("09:00", str(r.json()))

    def test_patient_signup_and_redirect(self):
        r = self.client.post(reverse("accounts:signup"), {"role": "patient", "first_name": "New", "last_name": "User", "email": "new@test.com", "phone": "", "password1": PASSWORD, "password2": PASSWORD, "accept_terms": "on"})
        self.assertRedirects(r, reverse("dashboard:home"), fetch_redirect_response=False)
        self.assertTrue(User.objects.get(email="new@test.com").is_patient)

    def test_doctor_signup_requires_specialty_and_license(self):
        data = {"role": "doctor", "first_name": "A", "last_name": "B", "email": "d2@test.com", "password1": PASSWORD, "password2": PASSWORD, "accept_terms": "on"}
        r = self.client.post(reverse("accounts:signup"), data)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(email="d2@test.com").exists())
        data.update(specialty=self.spec.pk, license_number="MD-99")
        self.client.post(reverse("accounts:signup"), data)
        self.assertTrue(Doctor.objects.filter(user__email="d2@test.com").exists())

    def test_signup_rejects_duplicate_email_and_mismatch(self):
        r = self.client.post(reverse("accounts:signup"), {"role": "patient", "first_name": "X", "last_name": "Y", "email": "PAT@test.com", "password1": PASSWORD, "password2": PASSWORD + "x", "accept_terms": "on"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="pat@test.com").count(), 1)

    def test_login(self):
        r = self.client.post(reverse("accounts:login"), {"username": "pat@test.com", "password": PASSWORD})
        self.assertEqual(r.status_code, 302)

    def test_booking_flow_and_double_booking(self):
        r = self.book(self.patient)
        appt = Appointment.objects.get()
        self.assertRedirects(r, reverse("appointments:detail", args=[appt.pk]), fetch_redirect_response=False)
        self.assertEqual(appt.status, Appointment.Status.PENDING)
        self.assertEqual(appt.fee, 100)
        r = self.book(self.other)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_booking_validation(self):
        self.assertEqual(self.book(self.patient, date=(timezone.localdate() - timedelta(days=1)).isoformat()).status_code, 200)
        self.assertEqual(self.book(self.patient, time="15:00").status_code, 200)
        self.assertEqual(self.book(self.patient, date=(self.monday + timedelta(days=1)).isoformat()).status_code, 200)
        self.assertEqual(self.book(self.patient, date=next_weekday(0).replace() + timedelta(days=70)).status_code, 200)
        self.assertFalse(Appointment.objects.exists())

    def test_role_restrictions(self):
        self.client.force_login(self.doc_user)
        self.assertNotEqual(self.client.get(reverse("records:list")).status_code, 200)
        self.client.force_login(self.patient)
        self.assertNotEqual(self.client.get(reverse("dashboard:doctor")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:patient")).status_code, 200)

    def test_appointment_privacy(self):
        self.book(self.patient)
        appt = Appointment.objects.get()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("appointments:detail", args=[appt.pk])).status_code, 404)

    def test_doctor_manages_appointment(self):
        self.book(self.patient)
        appt = Appointment.objects.get()
        self.client.force_login(self.doc_user)
        self.assertEqual(self.client.get(reverse("dashboard:doctor")).status_code, 200)
        self.client.post(reverse("appointments:quick_action", args=[appt.pk, "confirm"]))
        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.CONFIRMED)
        self.assertEqual(self.client.get(reverse("dashboard:patient_detail", args=[self.patient.pk])).status_code, 200)

    def test_patient_cancel(self):
        self.book(self.patient)
        appt = Appointment.objects.get()
        self.client.post(reverse("appointments:cancel", args=[appt.pk]))
        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.CANCELLED)
        self.book(self.other)
        self.assertEqual(Appointment.objects.count(), 2)

    def test_health_metric_validation(self):
        self.client.force_login(self.patient)
        url = reverse("records:metrics")
        now = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        self.client.post(url, {"metric_type": "blood_pressure", "value": "80", "value_secondary": "120", "recorded_at": now})
        self.assertFalse(HealthMetric.objects.exists())
        self.client.post(url, {"metric_type": "heart_rate", "value": "72", "recorded_at": now})
        self.assertEqual(HealthMetric.objects.count(), 1)

    def test_availability_overlap_rejected(self):
        self.client.force_login(self.doc_user)
        existing = self.doctor.availability.get()
        data = {"form-TOTAL_FORMS": "2", "form-INITIAL_FORMS": "1", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000",
                "form-0-id": existing.pk, "form-0-weekday": "0", "form-0-start_time": "09:00", "form-0-end_time": "11:00", "form-0-slot_minutes": "30", "form-0-is_active": "on",
                "form-1-weekday": "0", "form-1-start_time": "10:00", "form-1-end_time": "12:00", "form-1-slot_minutes": "30", "form-1-is_active": "on"}
        r = self.client.post(reverse("doctors:availability"), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.doctor.availability.count(), 1)
