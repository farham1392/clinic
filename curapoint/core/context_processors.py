from django.conf import settings
from django.utils.translation import gettext_lazy as _


def site(request):
    return {
        "SITE_NAME": "CuraPoint",
        "SITE_TAGLINE": _("Your health, one point of care"),
        "JS_I18N": {
            "noSlots": _("No free slots on this day. Please choose another date."),
            "at": _("at"),
            "noTime": _("No time selected"),
            "selectDate": _("Select a date to see available times."),
            "loading": _("Loading slots…"),
            "loadError": _("Could not load slots. Please retry."),
        },
        "SUPPORT_PHONE": getattr(settings, "SUPPORT_PHONE", "+1 (800) 555-0199"),
        "SUPPORT_EMAIL": getattr(settings, "SUPPORT_EMAIL", "care@curapoint.com"),
    }
