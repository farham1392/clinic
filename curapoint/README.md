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

On Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1   # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```
`ModuleNotFoundError: No module named 'whitenoise'` means the requirements were not installed in the Python you are running; run `python -m pip install -r requirements.txt`.

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

## Languages (English / فارسی)
The UI is bilingual. Use the globe button in the header to switch; Persian switches the layout to right-to-left and uses the Vazirmatn font. The browser's `Accept-Language` sets the language on the first visit.

Translations are in `locale/fa/LC_MESSAGES/django.po`. The compiled `django.mo` is committed, so you don't need gettext just to run the app. After changing strings:
```bash
python manage.py makemessages -l fa --ignore=.venv --ignore=staticfiles --ignore=static
# edit locale/fa/LC_MESSAGES/django.po
python manage.py compilemessages --ignore=.venv
```
Demo content (doctor names, bios, appointment reasons) stays in English; specialty names are translated.
