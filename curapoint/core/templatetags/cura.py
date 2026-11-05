from django import template

register = template.Library()


@register.filter
def stars(value):
    """Return a list of 'full' / 'half' / 'empty' for a 0-5 rating."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0
    out = []
    for i in range(1, 6):
        if v >= i:
            out.append("full")
        elif v >= i - 0.5:
            out.append("half")
        else:
            out.append("empty")
    return out


@register.filter
def add_class(field, css):
    return field.as_widget(attrs={**field.field.widget.attrs, "class": f"{field.field.widget.attrs.get('class', '')} {css}".strip()})


@register.simple_tag(takes_context=True)
def active(context, *url_names):
    match = getattr(context.get("request"), "resolver_match", None)
    if match and (match.view_name in url_names or any(match.view_name.startswith(n.rstrip("*")) for n in url_names if n.endswith("*"))):
        return "is-active"
    return ""


@register.filter
def percent(value, total):
    try:
        return int(round(100 * float(value) / float(total))) if float(total) else 0
    except (TypeError, ValueError):
        return 0


@register.filter
def avatar_color(obj):
    try:
        return f"c{int(obj.pk) % 6}"
    except (TypeError, ValueError, AttributeError):
        return "c1"
