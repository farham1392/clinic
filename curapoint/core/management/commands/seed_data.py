import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import PatientProfile, User
from appointments.models import Appointment
from doctors.models import Availability, Doctor, Review, Specialty
from records.models import HealthMetric, MedicalRecord

DEMO_PASSWORD = "Demo@1234"

SPECIALTIES = [
    ("Cardiology", "fa-heart-pulse", "Heart and blood vessel care"),
    ("Dermatology", "fa-hand-dots", "Skin, hair and nail conditions"),
    ("Pediatrics", "fa-baby", "Care for infants, children and teens"),
    ("Neurology", "fa-brain", "Brain, spine and nervous system"),
    ("Orthopedics", "fa-bone", "Bones, joints and muscles"),
    ("Dentistry", "fa-tooth", "Oral health and dental care"),
    ("Ophthalmology", "fa-eye", "Eye care and vision"),
    ("General Practice", "fa-stethoscope", "Primary and preventive care"),
    ("Psychiatry", "fa-head-side-virus", "Mental health and wellbeing"),
    ("Gynecology", "fa-person-pregnant", "Women's reproductive health"),
]

DOCTORS = [
    ("Sarah", "Johnson", "female", "Cardiology", "Senior Cardiologist", 15, 150, "HeartCare Center", "New York, NY", True),
    ("Michael", "Chen", "male", "Neurology", "Consultant Neurologist", 12, 180, "NeuroHealth Clinic", "San Francisco, CA", True),
    ("Emily", "Rodriguez", "female", "Pediatrics", "Pediatrician", 9, 110, "Little Stars Pediatrics", "Austin, TX", True),
    ("James", "Wilson", "male", "Orthopedics", "Orthopedic Surgeon", 18, 200, "Motion Orthopedics", "Chicago, IL", True),
    ("Aisha", "Patel", "female", "Dermatology", "Dermatologist", 8, 130, "Clear Skin Institute", "Seattle, WA", False),
    ("David", "Kim", "male", "Dentistry", "Cosmetic Dentist", 11, 95, "Bright Smile Dental", "Los Angeles, CA", False),
    ("Olivia", "Martinez", "female", "Ophthalmology", "Eye Specialist", 14, 140, "VisionFirst Eye Care", "Miami, FL", False),
    ("Robert", "Taylor", "male", "General Practice", "Family Physician", 20, 80, "CuraPoint Family Clinic", "Boston, MA", True),
    ("Fatima", "Hassan", "female", "Psychiatry", "Psychiatrist", 10, 160, "MindWell Center", "Denver, CO", False),
    ("Daniel", "Brown", "male", "Cardiology", "Interventional Cardiologist", 16, 170, "Pulse Heart Institute", "Houston, TX", False),
    ("Sophia", "Nguyen", "female", "Gynecology", "Obstetrician & Gynecologist", 13, 150, "Bloom Women's Health", "Portland, OR", False),
    ("Lucas", "Garcia", "male", "General Practice", "General Practitioner", 6, 70, "Downtown Health", "Phoenix, AZ", False),
]

PATIENTS = [
    ("Alex", "Morgan", "female", "1990-04-12"),
    ("Liam", "Carter", "male", "1985-09-30"),
    ("Mia", "Thompson", "female", "1998-01-22"),
    ("Noah", "Davis", "male", "1976-06-05"),
    ("Ava", "Lee", "female", "2001-11-17"),
    ("Ethan", "White", "male", "1993-03-08"),
]

REASONS = [
    "Annual check-up", "Follow-up consultation", "Chest discomfort", "Persistent headaches", "Skin rash",
    "Knee pain after running", "Blood test review", "Vaccination", "Blurred vision", "Back pain", "Anxiety and sleep issues",
]
COMMENTS = [
    "Very attentive and explained everything clearly.", "Excellent doctor, highly recommend!",
    "Short wait time and friendly staff.", "Took time to listen to all my concerns.",
    "Great experience, felt in good hands.", "Professional and thorough.",
]


class Command(BaseCommand):
    help = "Seed the database with demo specialties, doctors, patients, appointments, records and metrics."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing demo data before seeding.")

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(42)
        if opts["flush"]:
            Appointment.objects.all().delete()
            Review.objects.all().delete()
            MedicalRecord.objects.all().delete()
            HealthMetric.objects.all().delete()
            Doctor.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            Specialty.objects.all().delete()

        specs = {}
        for name, icon, desc in SPECIALTIES:
            specs[name], _ = Specialty.objects.update_or_create(name=name, defaults={"icon": icon, "description": desc})

        doctors = []
        for i, (first, last, gender, spec, title, years, fee, clinic, loc, featured) in enumerate(DOCTORS):
            email = "doctor@curapoint.com" if i == 0 else f"{first}.{last}@curapoint.com".lower()
            user, created = User.objects.get_or_create(email=email, defaults={"first_name": first, "last_name": last, "role": User.Role.DOCTOR, "gender": gender, "phone": f"+1 555 01{i:02d}"})
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            doctor, _ = Doctor.objects.update_or_create(user=user, defaults={
                "specialty": specs[spec], "title": title, "years_experience": years, "consultation_fee": Decimal(fee),
                "clinic_name": clinic, "location": loc, "is_featured": featured, "license_number": f"MD-{100200 + i}",
                "patients_served": 300 + years * 85, "offers_video": i % 3 != 2, "languages": random.choice(["English, Spanish", "English", "English, French", "English, Arabic", "English, Mandarin"]),
                "bio": (f"Dr. {first} {last} is a board-certified {title.lower()} with {years} years of experience at {clinic}. "
                        f"Known for a patient-first approach, Dr. {last} focuses on evidence-based treatment, preventive care and clear communication."),
                "education": "MD, Johns Hopkins University School of Medicine\nResidency, Massachusetts General Hospital\nBoard Certified, American Board of Medical Specialties",
            })
            if not doctor.availability.exists():
                days = [0, 1, 2, 3, 4] if i % 2 == 0 else [0, 2, 3, 4, 5]
                for d in days:
                    Availability.objects.create(doctor=doctor, weekday=d, start_time=time(9), end_time=time(12, 30), slot_minutes=30)
                    Availability.objects.create(doctor=doctor, weekday=d, start_time=time(14), end_time=time(17), slot_minutes=30)
            doctors.append(doctor)

        patients = []
        for i, (first, last, gender, dob) in enumerate(PATIENTS):
            email = "patient@curapoint.com" if i == 0 else f"{first}.{last}@example.com".lower()
            user, created = User.objects.get_or_create(email=email, defaults={"first_name": first, "last_name": last, "role": User.Role.PATIENT, "gender": gender, "date_of_birth": dob, "phone": f"+1 555 02{i:02d}", "address": f"{100 + i * 7} Main Street"})
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            PatientProfile.objects.update_or_create(user=user, defaults={
                "blood_type": random.choice(["A+", "O+", "B+", "AB+", "O-"]), "height_cm": random.randint(158, 188),
                "weight_kg": Decimal(random.randint(55, 92)), "allergies": random.choice(["", "Penicillin", "Peanuts", "Pollen"]),
                "chronic_conditions": random.choice(["", "Mild asthma", "Hypertension"]),
                "emergency_contact_name": "Jordan " + last, "emergency_contact_phone": "+1 555 0300",
            })
            patients.append(user)

        if not User.objects.filter(email="admin@curapoint.com").exists():
            User.objects.create_superuser("admin@curapoint.com", DEMO_PASSWORD, first_name="Site", last_name="Admin")

        if not Appointment.objects.exists():
            self._seed_appointments(doctors, patients)
        self._seed_records(doctors, patients)
        for d in doctors:
            d.refresh_rating()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Specialty.objects.count()} specialties, {Doctor.objects.count()} doctors, {len(patients)} patients, "
            f"{Appointment.objects.count()} appointments.\nDemo logins (password {DEMO_PASSWORD}): patient@curapoint.com, doctor@curapoint.com, admin@curapoint.com"
        ))

    def _free_slot(self, doctor, day):
        windows = list(doctor.availability.filter(weekday=day.weekday()))
        if not windows:
            return None
        taken = set(Appointment.objects.filter(doctor=doctor, date=day).exclude(status="cancelled").values_list("time", flat=True))
        candidates = []
        for w in windows:
            cur = datetime.combine(day, w.start_time)
            while cur + timedelta(minutes=w.slot_minutes) <= datetime.combine(day, w.end_time):
                if cur.time() not in taken:
                    candidates.append(cur.time())
                cur += timedelta(minutes=w.slot_minutes)
        return random.choice(candidates) if candidates else None

    def _book(self, doctor, patient, day, status):
        t = self._free_slot(doctor, day)
        if t is None:
            return None
        return Appointment.objects.create(
            doctor=doctor, patient=patient, date=day, time=t, status=status, fee=doctor.consultation_fee,
            reason=random.choice(REASONS), visit_type=random.choice(["in_person", "in_person", "video"]) if doctor.offers_video else "in_person",
            notes=random.choice(["", "Symptoms started last week.", "Currently taking ibuprofen.", ""]),
        )

    def _seed_appointments(self, doctors, patients):
        today = timezone.localdate()
        main_doc, main_patient = doctors[0], patients[0]
        # Today's schedule for the demo doctor
        for p, status in zip(patients, ["confirmed", "confirmed", "pending", "confirmed", "completed"]):
            if today.weekday() in main_doc.working_days():
                self._book(main_doc, p, today, status)
        # Past & future history across all doctors
        for doc in doctors:
            for _ in range(6):
                offset = random.randint(-60, -1)
                appt = self._book(doc, random.choice(patients), today + timedelta(days=offset), random.choice(["completed", "completed", "completed", "cancelled", "no_show"]))
                if appt and appt.status == "completed" and random.random() < 0.8:
                    review = Review.objects.create(doctor=doc, patient=appt.patient, appointment=appt, rating=random.choice([4, 5, 5, 5, 4, 3]), comment=random.choice(COMMENTS))
                    Review.objects.filter(pk=review.pk).update(created_at=timezone.make_aware(datetime.combine(appt.date, time(18))))
            for _ in range(4):
                self._book(doc, random.choice(patients), today + timedelta(days=random.randint(1, 21)), random.choice(["pending", "confirmed", "confirmed"]))
        # Guarantee demo patient has upcoming visits with several doctors
        for doc, status in zip(doctors[:4], ["confirmed", "pending", "confirmed", "pending"]):
            for offset in range(1, 15):
                day = today + timedelta(days=offset + doctors.index(doc) * 2)
                if day.weekday() in doc.working_days() and self._book(doc, main_patient, day, status):
                    break

    def _seed_records(self, doctors, patients):
        now = timezone.now()
        for p in patients:
            if not p.health_metrics.exists():
                base_hr, base_sys, base_glu, base_w = random.randint(64, 78), random.randint(112, 128), random.randint(85, 105), random.randint(60, 85)
                for k in range(7):
                    at = now - timedelta(days=(6 - k) * 5, hours=random.randint(0, 6))
                    HealthMetric.objects.create(patient=p, metric_type="heart_rate", value=base_hr + random.randint(-5, 5), recorded_at=at)
                    HealthMetric.objects.create(patient=p, metric_type="blood_pressure", value=base_sys + random.randint(-6, 6), value_secondary=random.randint(72, 84), recorded_at=at)
                    HealthMetric.objects.create(patient=p, metric_type="glucose", value=base_glu + random.randint(-8, 8), recorded_at=at)
                    HealthMetric.objects.create(patient=p, metric_type="weight", value=Decimal(base_w) + Decimal(random.randint(-10, 10)) / 10, recorded_at=at)
                    HealthMetric.objects.create(patient=p, metric_type="temperature", value=Decimal("36.6") + Decimal(random.randint(-3, 4)) / 10, recorded_at=at)
                    HealthMetric.objects.create(patient=p, metric_type="oxygen", value=random.randint(96, 99), recorded_at=at)
            if not p.medical_records.exists():
                done = Appointment.objects.filter(patient=p, status="completed").select_related("doctor")[:4]
                templates = [
                    ("diagnosis", "Seasonal allergic rhinitis", "Mild symptoms. Advised antihistamines and to avoid known triggers."),
                    ("prescription", "Amoxicillin 500mg", "Take one capsule three times daily for 7 days."),
                    ("lab_result", "Complete blood count", "All values within normal range. Hemoglobin 13.9 g/dL."),
                    ("vaccination", "Influenza vaccine", "Annual flu shot administered, left arm. No adverse reaction."),
                ]
                for appt, (rtype, title, desc) in zip(done, templates):
                    MedicalRecord.objects.create(patient=p, doctor=appt.doctor, appointment=appt, record_type=rtype, title=title, description=desc, record_date=appt.date)
