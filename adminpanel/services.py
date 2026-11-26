"""Admin dashboard figures and monitoring helpers (spec §§11.2, 11.6–11.8)."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.db.models import Count, Exists, OuterRef

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


def student_outcomes(counts: dict) -> list[dict]:
    """The qualified / not qualified / not attempted split as bar segments; widths are shares of all students."""
    parts = [("qualified", "Qualified", counts["qualified_students"]),
             ("not-qualified", "Not qualified", counts["not_qualified_students"]),
             ("not-attempted", "Not attempted", counts["not_attempted_students"])]
    total = sum(n for _, _, n in parts)
    return [{"key": k, "label": label, "n": n, "width": f"{(n / total * 100) if total else 0:.2f}"}
            for k, label, n in parts]


def recommendations_per_internship(limit: int = 8) -> list[tuple[str, int]]:
    """Internships that appear most often in stored recommendation rows: [("Title @ Company", rows)],
    highest first. The company is part of the label because many listings share a title."""
    rows = (InternshipRecommendation.objects
            .values("internship_id", "internship__internship_title", "internship__company_name")
            .annotate(n=Count("id")).order_by("-n", "internship__internship_title", "internship__company_name")[:limit])
    return [(f'{r["internship__internship_title"]} @ {r["internship__company_name"]}', r["n"]) for r in rows]


MIN_RUNS_FOR_CHART = 3


def recommendations_chart(per_internship: list[tuple[str, int]], runs: int) -> dict | None:
    """Chart data, or None when it would say nothing: fewer than MIN_RUNS_FOR_CHART runs, or every
    internship recommended equally often (Phase 6.5)."""
    counts = [n for _, n in per_internship]
    if runs < MIN_RUNS_FOR_CHART or len(set(counts)) <= 1:
        return None
    return {"labels": [t for t, _ in per_internship], "values": counts}


def _png_size(path: Path) -> tuple[int, int] | None:
    """Width and height from a PNG's IHDR chunk (no image library needed)."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def figure_entries() -> list[dict]:
    """Listed figures with a `wide` flag: multi-panel figures (wider than 2.5:1) span the full row.
    Ordinary single charts in the notebook are 2.03:1 or narrower; the multi-panel ones are 2.9:1 and up."""
    out = []
    for name in listed_figures():
        size = _png_size(artifacts_dir() / "figures" / name)
        out.append({"name": name, "wide": bool(size and size[1] and size[0] / size[1] > 2.5),
                    "width": size[0] if size else None, "height": size[1] if size else None})
    return out


def model_comparison(metrics: dict | None) -> dict | None:
    """Accuracy and macro F1 per saved model, as percentages, straight from metrics.json."""
    models = (metrics or {}).get("models") or {}
    if not models:
        return None
    names = list(models)
    return {"labels": names,
            "accuracy": [round(models[n]["accuracy"] * 100, 1) for n in names],
            "f1_macro": [round(models[n]["f1_macro"] * 100, 1) for n in names]}


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
