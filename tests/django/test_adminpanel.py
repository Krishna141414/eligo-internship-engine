"""Admin module: dashboard counts, student management, monitoring pages (spec §§11.2–11.8). Fixtures only."""
import html
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from adminpanel.services import dashboard_counts
from assessments.models import Assessment, Attempt
from internships.models import Internship
from recommendations import services as rec_services
from recommendations.models import InternshipRecommendation
from students.models import StudentProfile
from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


def _attempt(student, score, result, minutes_ago=0):
    a, _ = Assessment.objects.get_or_create(assessment_name="Aptitude (fixture)",
                                            defaults=dict(qualification="Any Graduate", duration_minutes=10, status="ACTIVE"))
    when = timezone.now() - timedelta(minutes=minutes_ago)
    return Attempt.objects.create(student=student, assessment=a, start_time=when - timedelta(minutes=5), deadline=when,
                                  submission_time=when, status="SUBMITTED", total_marks=5, obtained_marks=3,
                                  score_percentage=Decimal(score), result=result)


def test_dashboard_counts_match_db(student, other_student, make_user):
    third = make_user(email="third@example.com")
    _attempt(student, "40", "NOT_QUALIFIED", minutes_ago=30)
    _attempt(student, "80", "QUALIFIED", minutes_ago=5)            # has a qualifying attempt -> qualified
    _attempt(other_student, "60.00", "NOT_QUALIFIED", minutes_ago=30)
    _attempt(other_student, "50", "NOT_QUALIFIED", minutes_ago=5)  # attempted, never above 60% -> not qualified
    Internship.objects.create(company_name="A", internship_title="X", job_role="X", description="d", location="L")
    Internship.objects.create(company_name="B", internship_title="Y", job_role="Y", description="d", location="L",
                              status="INACTIVE")
    c = dashboard_counts()
    assert c == {"total_students": 3, "total_internships": 2, "active_internships": 1, "total_assessments": 1,
                 "qualified_students": 1, "not_qualified_students": 1, "not_attempted_students": 1,
                 "total_recommendations": 0, "recommendation_runs": 0, "total_predictions": 0}
    assert third.pk  # third student never attempted


def test_dashboard_page_shows_counts(admin_client_, student):
    html_ = admin_client_.get(reverse("adminpanel:dashboard")).content.decode()
    assert "Total students" in html_ and "Qualified" in html_


def test_admin_can_deactivate_student_and_student_cannot_login(admin_client_, student):
    from django.test import Client
    resp = admin_client_.post(reverse("adminpanel:student_toggle", args=[student.pk]))
    student.refresh_from_db()
    assert resp.status_code == 302 and student.status == "INACTIVE" and not student.is_active
    resp = Client().post(reverse("accounts:login"), {"username": student.email, "password": PASSWORD})
    assert "Your account is inactive" in html.unescape(resp.content.decode())
    admin_client_.post(reverse("adminpanel:student_toggle", args=[student.pk]))
    student.refresh_from_db()
    assert student.status == "ACTIVE"


def test_toggle_requires_post_and_ignores_admins(admin_client_, admin_user):
    assert admin_client_.get(reverse("adminpanel:student_toggle", args=[admin_user.pk])).status_code == 405
    assert admin_client_.post(reverse("adminpanel:student_toggle", args=[admin_user.pk])).status_code == 404


def test_student_list_and_detail(admin_client_, student):
    StudentProfile.objects.create(student=student, qualification="B.Tech", academic_percentage=Decimal("71"),
                                  skills=["python"], career_skills=["machine learning"])
    _attempt(student, "80", "QUALIFIED")
    assert student.email in admin_client_.get(reverse("adminpanel:students")).content.decode()
    page = admin_client_.get(reverse("adminpanel:student_detail", args=[student.pk])).content.decode()
    for text in ("B.Tech", "71", "python", "machine learning", "80.00%"):
        assert text in page


def test_results_monitoring_filters_by_result(admin_client_, student, other_student):
    _attempt(student, "80", "QUALIFIED")
    _attempt(other_student, "40", "NOT_QUALIFIED")
    page = admin_client_.get(reverse("adminpanel:results"), {"result": "QUALIFIED"}).content.decode()
    assert student.email in page and other_student.email not in page


def test_recommendation_monitoring_shows_scores_and_explanation(admin_client_, student, ai_bundle):
    StudentProfile.objects.create(student=student, qualification="B.Tech", academic_percentage=Decimal("75"),
                                  skills=["python", "sql"])
    _attempt(student, "80", "QUALIFIED")
    run = rec_services.generate_recommendations(student)
    rec = InternshipRecommendation.objects.filter(run_id=run.run_id, recommendation_rank=1).get()
    page = html.unescape(admin_client_.get(reverse("adminpanel:recommendations")).content.decode())
    assert student.email in page and rec.internship.internship_title in page
    detail = html.unescape(admin_client_.get(reverse("adminpanel:recommendation_detail", args=[rec.pk])).content.decode())
    assert rec.recommendation_reason in detail and "python" in detail


def test_ml_page_shows_metrics_and_figures(admin_client_, fake_artifacts):
    (fake_artifacts / "figures" / "model_comparison.png").write_bytes(b"\x89PNG fake")
    from ml_core.artifacts import write_manifest
    write_manifest(fake_artifacts, best_model_name="RandomForestClassifier", model_version="1", sentence_model_revision="x")
    rec_services.reset_bundle_cache()
    page = admin_client_.get(reverse("adminpanel:ml")).content.decode()
    assert "RandomForestClassifier" in page and "model_comparison.png" in page
    resp = admin_client_.get(reverse("adminpanel:figure", args=["model_comparison.png"]))
    assert resp.status_code == 200 and resp["Content-Type"] == "image/png"


def test_figure_view_rejects_path_traversal(admin_client_, fake_artifacts):
    assert admin_client_.get(reverse("adminpanel:figure", args=["..%2Fmanifest.json"])).status_code == 404
    assert admin_client_.get("/manage/ml/figures/../manifest.json").status_code == 404
    assert admin_client_.get(reverse("adminpanel:figure", args=["not_listed.png"])).status_code == 404


def test_ml_page_without_artifacts_shows_message(admin_client_):
    page = admin_client_.get(reverse("adminpanel:ml")).content.decode()
    assert "Run the notebook" in page


@pytest.mark.parametrize("name", ["dashboard", "students", "results", "recommendations", "ml"])
def test_admin_pages_forbidden_to_students(student_client, name):
    assert student_client.get(reverse(f"adminpanel:{name}")).status_code == 403
