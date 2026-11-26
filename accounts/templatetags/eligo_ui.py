"""Small template helpers for the Eligo UI shell."""
import hashlib
from functools import lru_cache
from pathlib import Path

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static
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


@register.filter
def mmss(seconds):
    """754 -> '12:34' (the exam timer's first, server-rendered value)."""
    try:
        s = max(0, int(seconds))
    except (TypeError, ValueError):
        return ""
    return f"{s // 60}:{s % 60:02d}"


@lru_cache(maxsize=256)
def _digest(path: str, mtime: float) -> str:          # keyed by mtime, so an edited file gets a new version
    found = finders.find(path)
    return hashlib.sha256(Path(found).read_bytes()).hexdigest()[:12] if found else "0"


@register.simple_tag
def asset(path):
    """Static URL with a content-hash version (?v=...) so browsers never keep a stale copy of our own CSS/JS
    after an update (found while taking the Phase 6.5 check shots)."""
    found = finders.find(path)
    mtime = Path(found).stat().st_mtime if found else 0.0
    return f"{static(path)}?v={_digest(path, mtime)}"
