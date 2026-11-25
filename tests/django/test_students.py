"""Student profile (incl. D-022 career skills) and dashboard (spec §§12.1–12.3)."""
import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from assessments.models import Assessment, Attempt, Question
from students.forms import CAREER_SKILLS_LABEL, StudentProfileForm
from students.models import StudentProfile
from students.services import dashboard_context

pytestmark = pytest.mark.django_db

VALID = {"qualification": "B.Tech", "specialization": "CSE", "college_name": "Fixture College",
         "academic_percentage": "78.5", "skills": "Python, SQL", "career_skills": ["python", "machine learning"],
         "career_interests": "AI", "preferred_job_role": "ML Engineer", "preferred_location": "Pune"}


def _schema_vocab(root):
    return json.loads((root / "config" / "feature_schema.json").read_text())["input"]["skills"]["vocabulary"]


# --- profile form ------------------------------------------------------------------------------------
def test_profile_saves_free_text_and_career_skills_separately(student_client, student, fake_artifacts):
    resp = student_client.post(reverse("students:profile_edit"), VALID)
    assert resp.status_code == 302
    p = StudentProfile.objects.get(student=student)
    assert p.skills == ["python", "sql"]
    assert p.career_skills == ["machine learning", "python"]


def test_profile_rejects_percentage_over_100(student_client, fake_artifacts):
    resp = student_client.post(reverse("students:profile_edit"), dict(VALID, academic_percentage="101"))
    assert resp.status_code == 200 and not StudentProfile.objects.exists()


def test_profile_rejects_unknown_skill_with_suggestions(student_client, fake_artifacts):
    resp = student_client.post(reverse("students:profile_edit"), dict(VALID, skills="Pythn"))
    html = resp.content.decode()
    assert resp.status_code == 200 and "pythn" in html.lower() and "python" in html


def test_profile_requires_qualification_with_friendly_message(student_client, fake_artifacts):
    resp = student_client.post(reverse("students:profile_edit"), dict(VALID, qualification=""))
    assert "Your profile is missing qualification. Add it to see matches." in resp.content.decode()


def test_career_skill_choices_come_from_model_schema(fake_artifacts):
    form = StudentProfileForm()
    assert [c for c, _ in form.fields["career_skills"].choices] == _schema_vocab(fake_artifacts)
    assert form.fields["career_skills"].label == CAREER_SKILLS_LABEL == "Skills the job-role model understands"


def test_career_skills_reject_value_not_in_model_vocab(student_client, fake_artifacts):
    resp = student_client.post(reverse("students:profile_edit"), dict(VALID, career_skills=["cooking"]))
    assert resp.status_code == 200 and not StudentProfile.objects.exists()


def test_career_skills_suggested_from_free_text_skills(student_client, student, fake_artifacts):
    StudentProfile.objects.create(student=student, qualification="B.Tech", skills=["python", "sql"])
    resp = student_client.get(reverse("students:profile_edit"))
    form = resp.context["form"]
    assert form.initial["career_skills"] == ["python"]           # sql's crosswalk targets aren't in the fake vocab
    assert resp.context["suggested_career_skills"] == ["python"]


def test_career_skills_page_explains_their_purpose(student_client, fake_artifacts):
    html = student_client.get(reverse("students:profile_edit")).content.decode()
    assert "Skills the job-role model understands" in html and "internship matching" in html


# --- dashboard / journey -------------------------------------------------------------------------------
def _assessment():
    a = Assessment.objects.create(assessment_name="Graduate aptitude (fixture)", qualification="Any Graduate",
                                  duration_minutes=10, status="ACTIVE")
    Question.objects.create(assessment=a, question_text="?", option_a="a", option_b="b", option_c="c",
                            option_d="d", correct_option="A")
    return a


def _finished_attempt(student, a, score, result):
    now = timezone.now()
    return Attempt.objects.create(student=student, assessment=a, start_time=now - timedelta(minutes=5),
                                  deadline=now + timedelta(minutes=5), submission_time=now, status="SUBMITTED",
                                  total_marks=1, obtained_marks=1, score_percentage=Decimal(score), result=result)


def _states(ctx):
    return [s["state"] for s in ctx["journey"]]


def test_journey_states_progress(student):
    assert _states(dashboard_context(student)) == ["current", "pending", "pending", "pending", "pending"]
    StudentProfile.objects.create(student=student, qualification="B.Tech", academic_percentage=Decimal("70"),
                                  skills=["python"])
    assert _states(dashboard_context(student))[:2] == ["done", "current"]
    a = _assessment()
    _finished_attempt(student, a, "55", "NOT_QUALIFIED")
    assert _states(dashboard_context(student))[:3] == ["done", "done", "current"]
    _finished_attempt(student, a, "80", "QUALIFIED")
    assert _states(dashboard_context(student))[:4] == ["done", "done", "done", "current"]


def test_dashboard_lists_available_assessments_for_qualification(student):
    StudentProfile.objects.create(student=student, qualification="B.Tech", academic_percentage=Decimal("70"),
                                  skills=["python"])
    _assessment()
    Assessment.objects.create(assessment_name="MBA only (fixture)", qualification="MBA", duration_minutes=5,
                              status="ACTIVE").questions.create(question_text="?", option_a="a", option_b="b",
                                                                option_c="c", option_d="d", correct_option="A")
    names = [a.assessment_name for a in dashboard_context(student)["available_assessments"]]
    assert names == ["Graduate aptitude (fixture)"]


def test_dashboard_only_shows_own_data(student_client, student, other_student):
    a = _assessment()
    _finished_attempt(other_student, a, "91", "QUALIFIED")
    html = student_client.get(reverse("students:dashboard")).content.decode()
    assert "91.00%" not in html
    assert dashboard_context(student)["latest_attempt"] is None
