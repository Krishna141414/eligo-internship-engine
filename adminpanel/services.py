"""Admin dashboard figures and monitoring helpers (spec §§11.2, 11.6–11.8)."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.db.models import Exists, OuterRef

from accounts.models import User
from assessments.models import Assessment, Attempt
from assessments.services import FINISHED
from internships.models import Internship
from recommendations.models import InternshipRecommendation, JobRolePrediction


def students():
    """Student users annotated with qualified (any attempt > 60%) and attempted flags.
    'Qualified' uses the same rule as the eligibility gate, so the two never disagree."""
    finished = Attempt.objects.filter(student=OuterRef("pk"), status__in=FINISHED)
    return (User.objects.filter(user_type=User.UserType.STUDENT)
            .annotate(attempted=Exists(finished), qualified=Exists(finished.filter(result=Attempt.Result.QUALIFIED))))


def dashboard_counts() -> dict:
    s = students()
    return {
        "total_students": s.count(),
        "total_internships": Internship.objects.count(),
        "active_internships": Internship.objects.active().count(),
        "total_assessments": Assessment.objects.count(),
        "qualified_students": s.filter(qualified=True).count(),
        "not_qualified_students": s.filter(attempted=True, qualified=False).count(),
        "not_attempted_students": s.filter(attempted=False).count(),
        "total_recommendations": InternshipRecommendation.objects.count(),
        "recommendation_runs": InternshipRecommendation.objects.values("run_id").distinct().count(),
        "total_predictions": JobRolePrediction.objects.count(),
    }


def artifacts_dir() -> Path:
    return Path(settings.ELIGO_ARTIFACTS_DIR)


def read_manifest() -> dict | None:
    try:
        return json.loads((artifacts_dir() / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_metrics() -> dict | None:
    from recommendations.services import get_bundle

    bundle, _ = get_bundle()
    if bundle is not None:
        return bundle.metrics
    try:
        return json.loads((artifacts_dir() / "metrics" / "metrics.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def listed_figures() -> list[str]:
    """PNG files under figures/ that the manifest lists (only these can be served)."""
    manifest = read_manifest() or {}
    return sorted(PurePosixPath(k).name for k in manifest.get("files", {})
                  if k.startswith("figures/") and k.endswith(".png") and "/" not in k[len("figures/"):])


def figure_path(name: str) -> Path | None:
    """Resolve a figure name to a file, only if the manifest lists it and it stays inside figures/."""
    if name not in listed_figures():
        return None
    root = (artifacts_dir() / "figures").resolve()
    path = (root / name).resolve()
    return path if path.parent == root and path.is_file() else None
