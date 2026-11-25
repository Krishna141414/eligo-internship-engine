"""Student-side helpers: profile facts for the gates, career-skill vocabulary, dashboard data."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.urls import NoReverseMatch, reverse

from ml_core.eligibility import StudentFacts
from ml_core.preprocessing import build_student_text
from students.models import StudentProfile


def get_profile(user) -> StudentProfile | None:
    return StudentProfile.objects.filter(student=user).first()


def student_facts(profile: StudentProfile) -> StudentFacts:
    skills = tuple(profile.skills or ())
    return StudentFacts(
        qualification=profile.qualification, specialization=profile.specialization,
        academic_percentage=Decimal(profile.academic_percentage or 0), skills=skills,
        text=build_student_text(skills, profile.career_interests, profile.preferred_job_role, profile.specialization))


def career_skill_vocab() -> list[str]:
    """The job-role model's own skill vocabulary (feature_schema.json, D-022). Empty if artifacts are missing."""
    from recommendations.services import get_bundle

    bundle, _ = get_bundle()
    if bundle is not None:
        return list(bundle.feature_schema["input"]["skills"]["vocabulary"])
    try:
        schema = json.loads((Path(settings.ELIGO_ARTIFACTS_DIR) / "config" / "feature_schema.json").read_text("utf-8"))
        return list(schema["input"]["skills"]["vocabulary"])
    except (OSError, ValueError, KeyError):
        return []


def _url(name: str) -> str:
    try:
        return reverse(name)
    except NoReverseMatch:
        return ""


def dashboard_context(user) -> dict:
    from assessments.models import Attempt
    from assessments.services import FINISHED, _matching, available_assessments, latest_qualifying_attempt
    from internships.models import Internship
    from recommendations.models import InternshipRecommendation, JobRolePrediction

    profile = get_profile(user)
    missing = profile.missing_fields() if profile else ["qualification", "academic percentage", "skills"]
    qualification = profile.qualification if profile else ""
    profile_done = not missing
    attempted = profile_done and _matching(user, qualification).exists()
    qualifying = latest_qualifying_attempt(user, qualification) if profile_done else None
    latest_rec = InternshipRecommendation.objects.filter(student=user).order_by("-generated_date").first()
    latest_prediction = JobRolePrediction.objects.filter(student=user).first()

    steps = [("profile", "Profile", profile_done, "students:profile_edit", "Complete your profile"),
             ("assessment", "Assessment", attempted, "assessments:list", "Take an assessment"),
             ("eligibility", "Eligibility", qualifying is not None, "assessments:list",
              "Score above 60% on an assessment"),
             ("recommendations", "Recommendations", latest_rec is not None, "recommendations:list",
              "Generate your recommendations"),
             ("job_role", "Job role", latest_prediction is not None, "recommendations:job_role",
              "Predict your job role")]
    journey, blocked = [], False
    for key, label, done, url, action in steps:
        state = "done" if done and not blocked else ("pending" if blocked else "current")
        blocked = blocked or not done
        journey.append({"key": key, "label": label, "state": state, "url": _url(url), "action": action})
    next_step = next((s for s in journey if s["state"] == "current"), None)

    latest_recommendations, n_recommendations = [], 0
    if latest_rec is not None:
        run = InternshipRecommendation.objects.filter(student=user, run_id=latest_rec.run_id)
        n_recommendations = run.count()
        latest_recommendations = list(run.select_related("internship").order_by("recommendation_rank")[:3])
    assessments = list(available_assessments(qualification))
    return {
        "profile": profile,
        "missing": missing,
        "journey": journey,
        "next_step": next_step,
        "available_assessments": assessments,
        "available_internships_count": Internship.objects.active().count(),
        "latest_attempt": Attempt.objects.filter(student=user, status__in=FINISHED).select_related("assessment").first(),
        "qualifying_attempt": qualifying,
        "latest_recommendations": latest_recommendations,
        "latest_prediction": latest_prediction,
        "stats": {"internships": Internship.objects.active().count(), "assessments": len(assessments),
                  "recommendations": n_recommendations},
    }
