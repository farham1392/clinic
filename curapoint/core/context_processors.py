from django.conf import settings


def site(request):
    return {
        "SITE_NAME": "CuraPoint",
        "SITE_TAGLINE": "Your health, one point of care",
        "SUPPORT_PHONE": getattr(settings, "SUPPORT_PHONE", "+1 (800) 555-0199"),
        "SUPPORT_EMAIL": getattr(settings, "SUPPORT_EMAIL", "care@curapoint.com"),
    }
