# CuraPoint

Doctor discovery and appointment booking platform built with Django 5 and SQLite.

## Features
- Email-based custom user model with **patient** and **doctor** roles
- Doctor directory with search, specialty/location/rating filters and sorting
- Doctor profiles with education, languages, reviews, weekly hours and live slot picker
- Appointment booking with server-side validation (future dates, 60-day window, doctor hours, no double-booking)
- Patient dashboard: next visit, health metrics with trend sparklines, records, visit history
- Doctor dashboard: today's schedule, request approval, weekly chart, revenue, reviews, patient charts
- Medical records, health metrics, availability management, Django admin for everything

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data          # add --flush to reset demo data
python manage.py runserver
```
Open http://127.0.0.1:8000

| Role    | Email                  | Password  |
|---------|------------------------|-----------|
| Patient | patient@curapoint.com  | Demo@1234 |
| Doctor  | doctor@curapoint.com   | Demo@1234 |
| Admin   | admin@curapoint.com    | Demo@1234 |

## Tests
```bash
python manage.py test
```

## Project layout
```
curapoint/      settings, root URLs
accounts/       User model, auth, signup, profile
doctors/        Specialty, Doctor, Availability, Review, listing/profile/slots
appointments/   Appointment model, booking, status management
records/        MedicalRecord, HealthMetric
dashboard/      patient & doctor dashboards, patient charts
core/           landing page, template tags, decorators, seed_data command
templates/      base.html, app_base.html, partials/, per-app templates
static/         css/main.css, js/main.js, img/, vendor/ (Font Awesome, Inter)
```

## Production
Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, then:
```bash
python manage.py collectstatic --noinput
gunicorn curapoint.wsgi
```
Static files are served by WhiteNoise.
