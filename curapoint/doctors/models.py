from datetime import datetime, timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.text import slugify


class Specialty(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    icon = models.CharField(max_length=50, default="fa-stethoscope", help_text="Font Awesome icon class")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "specialties"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class DoctorQuerySet(models.QuerySet):
    def active(self):
        return self.filter(user__is_active=True)

    def with_stats(self):
        return self.annotate(avg_rating=Avg("reviews__rating"), review_total=Count("reviews", distinct=True))


class Doctor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_profile")
    slug = models.SlugField(max_length=120, unique=True)
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, related_name="doctors")
    title = models.CharField(max_length=120, blank=True, help_text="e.g. Senior Cardiologist")
    bio = models.TextField(blank=True)
    education = models.TextField(blank=True, help_text="One entry per line")
    languages = models.CharField(max_length=200, default="English")
    license_number = models.CharField(max_length=50, blank=True)
    years_experience = models.PositiveSmallIntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    clinic_name = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to="doctors/", blank=True)
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    review_count = models.PositiveIntegerField(default=0)
    patients_served = models.PositiveIntegerField(default=0)
    offers_video = models.BooleanField(default=True)
    is_accepting_patients = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = DoctorQuerySet.as_manager()

    class Meta:
        ordering = ["-is_featured", "-rating", "user__first_name"]

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

    @property
    def name(self):
        return str(self)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"dr-{self.user.first_name}-{self.user.last_name}") or "doctor"
            slug, n = base, 2
            while Doctor.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("doctors:detail", kwargs={"slug": self.slug})

    @property
    def education_list(self):
        return [line.strip() for line in self.education.splitlines() if line.strip()]

    @property
    def language_list(self):
        return [lang.strip() for lang in self.languages.split(",") if lang.strip()]

    @property
    def rating_stars(self):
        full = int(round(float(self.rating)))
        return [i < full for i in range(5)]

    def refresh_rating(self):
        stats = self.reviews.aggregate(avg=Avg("rating"), n=Count("id"))
        self.rating = round(stats["avg"] or 0, 2)
        self.review_count = stats["n"]
        self.save(update_fields=["rating", "review_count"])

    def working_days(self):
        return sorted({a.weekday for a in self.availability.filter(is_active=True)})

    def slots_for(self, day):
        """All bookable start times for a date, excluding already booked slots and past times."""
        from appointments.models import Appointment
        from django.utils import timezone

        windows = self.availability.filter(weekday=day.weekday(), is_active=True)
        taken = set(
            Appointment.objects.filter(doctor=self, date=day)
            .exclude(status=Appointment.Status.CANCELLED)
            .values_list("time", flat=True)
        )
        now = timezone.localtime()
        slots = []
        for window in windows:
            current = datetime.combine(day, window.start_time)
            end = datetime.combine(day, window.end_time)
            step = timedelta(minutes=window.slot_minutes)
            while current + step <= end:
                t = current.time()
                in_past = day < now.date() or (day == now.date() and t <= now.time())
                if t not in taken and not in_past:
                    slots.append(t)
                current += step
        return sorted(set(slots))

    def next_available(self, days=30):
        from django.utils import timezone

        today = timezone.localdate()
        for offset in range(days):
            day = today + timedelta(days=offset)
            slots = self.slots_for(day)
            if slots:
                return datetime.combine(day, slots[0])
        return None


class Availability(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="availability")
    weekday = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(10), MaxValueValidator(240)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name_plural = "availability"
        constraints = [
            models.CheckConstraint(check=models.Q(end_time__gt=models.F("start_time")), name="availability_end_after_start"),
        ]

    def __str__(self):
        return f"{self.doctor} - {self.get_weekday_display()} {self.start_time:%H:%M}-{self.end_time:%H:%M}"


class Review(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="reviews")
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.SET_NULL, null=True, blank=True, related_name="review"
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}★ for {self.doctor} by {self.patient}"
