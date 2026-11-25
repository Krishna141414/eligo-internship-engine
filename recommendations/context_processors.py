"""Adds the AI engine status to every template so a friendly banner can be shown (hard rule 13)."""
from recommendations.services import ai_status as _ai_status


def ai_status(request):
    status = _ai_status()
    return {"ai_ok": status.ok, "ai_message": status.message}
