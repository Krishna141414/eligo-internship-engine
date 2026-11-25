"""Small template helpers for the Eligo UI shell."""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def current(context, *view_names):
    """aria-current="page" when the request resolved to one of `view_names` (namespace:name, or
    namespace:* for a whole section)."""
    match = getattr(context.get("request"), "resolver_match", None)
    if match is None:
        return ""
    name = match.view_name
    for v in view_names:
        if v == name or (v.endswith(":*") and name.startswith(v[:-1])):
            return mark_safe(' aria-current="page"')
    return ""


@register.filter
def pct(value, places=0):
    """0.651 -> '65' (a 0-1 score shown as a whole percentage)."""
    try:
        return f"{float(value) * 100:.{int(places)}f}"
    except (TypeError, ValueError):
        return ""


@register.filter
def as_percent_width(value):
    """0.231 -> '23.10' for inline widths (CSS custom properties), clamped to 0-100."""
    try:
        return f"{max(0.0, min(100.0, float(value) * 100)):.2f}"
    except (TypeError, ValueError):
        return "0"
