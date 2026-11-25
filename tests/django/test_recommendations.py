"""AI integration: recommendations, job-role prediction (career skills only), caching, isolation
(spec §§12.7–12.8, 13, 14; rules 3, 4, 11, 13, 15; D-014, D-015, D-021, D-022). All data are fixtures."""
import html
from datetime import timedelta
from decimal import Decimal

import numpy as np
import pytest
from django.urls import reverse
from django.utils import timezone

from assessments.models import Assessment, Attempt
from internships.models import Internship
from recommendations import services
from recommendations.models import InternshipRecommendation, JobRolePrediction
from students.models import StudentProfile

pytestmark = pytest.mark.django_db


def _profile(student, **kw):
    base = dict(qualification="B.Tech", specialization="CSE", academic_percentage=Decimal("75"),
                skills=["python", "sql"], career_skills=["machine learning", "python", "statistics"],
                career_interests="data", preferred_job_role="Data Scientist")
    base.update(kw)
    return StudentProfile.objects.create(student=student, **base)


def _qualify(student, score="72.5"):
    a, _ = Assessment.objects.get_or_create(assessment_name="Graduate aptitude (fixture)",
                                            defaults=dict(qualification="Any Graduate", duration_minutes=10, status="ACTIVE"))
    now = timezone.now()
    return Attempt.objects.create(student=student, assessment=a, start_time=now - timedelta(minutes=5),
                                  deadline=now, submission_time=now, status="SUBMITTED", total_marks=5,
                                  obtained_marks=4, score_percentage=Decimal(score),
                                  result="QUALIFIED" if Decimal(score) > 60 else "NOT_QUALIFIED")


# --- graceful degradation -----------------------------------------------------------------------------
def test_recommendations_page_without_artifacts_shows_banner(student_client, student):
    _profile(student)
    _qualify(student)
    resp = student_client.get(reverse("recommendations:list"))
    assert resp.status_code == 200 and "AI engine unavailable" in resp.content.decode()
    resp = student_client.post(reverse("recommendations:list"), follow=True)
    assert resp.status_code == 200 and not InternshipRecommendation.objects.exists()
    assert student_client.get(reverse("recommendations:job_role")).status_code == 200


# --- recommendations -----------------------------------------------------------------------------------
def test_no_qualifying_attempt_returns_reason_and_no_rows(student, ai_bundle):
    _profile(student)
    _qualify(student, "60.00")
    run = services.generate_recommendations(student)
    assert run.eligible == [] and "more than 60%" in run.reason
    assert not InternshipRecommendation.objects.exists()


def test_incomplete_profile_returns_reason(student, ai_bundle):
    StudentProfile.objects.create(student=student)
    run = services.generate_recommendations(student)
    assert run.eligible == [] and "Complete your profile" in run.reason


def test_generate_saves_run_with_only_eligible_ranked(student, ai_bundle):
    _profile(student)
    attempt = _qualify(student)
    run = services.generate_recommendations(student)
    rows = list(InternshipRecommendation.objects.filter(run_id=run.run_id).order_by("recommendation_rank"))
    titles = [r.internship.internship_title for r in rows]
    assert "MBA Strategy Intern" not in titles                      # requires MBA -> gated out
    assert set(titles) == {"Data Science", "Web Development"}
    assert [r.recommendation_rank for r in rows] == [1, 2] and rows[0].internship.internship_title == "Data Science"
    top = rows[0]
    assert top.assessment_attempt == attempt and top.matched_skills == ["python", "sql"] and top.missing_skills == []
    assert top.final_match_score == pytest.approx(sum(c["contribution"] for c in top.explanation["components"]))
    assert top.analysis_method == "rule_based"
    assert run.not_eligible_count == 1


def test_not_eligible_preview_shows_skill_sharing_internships_with_reasons(student, ai_bundle):
    _profile(student, skills=["python", "sql", "excel"])
    _qualify(student)
    run = services.generate_recommendations(student)
    assert [(i.internship_title, reasons) for i, reasons in run.not_eligible] == [
        ("MBA Strategy Intern", ["Requires MBA; your qualification is B.Tech."])]


def test_rerun_keeps_previous_run(student, ai_bundle):
    _profile(student)
    _qualify(student)
    first = services.generate_recommendations(student)
    second = services.generate_recommendations(student)
    assert first.run_id != second.run_id
    assert InternshipRecommendation.objects.filter(run_id=first.run_id).count() == 2
    assert InternshipRecommendation.objects.filter(run_id=second.run_id).count() == 2


def test_list_view_shows_latest_run_and_method(student_client, student, ai_bundle):
    _profile(student)
    _qualify(student)
    student_client.post(reverse("recommendations:list"))
    page = html.unescape(student_client.get(reverse("recommendations:list")).content.decode())
    assert "Data Science" in page and "Rule-based" in page and "Why you can't apply yet" in page


def test_other_students_recommendation_is_404(client, student, other_student, ai_bundle):
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    rec = InternshipRecommendation.objects.filter(run_id=run.run_id).first()
    client.force_login(other_student)
    assert client.get(reverse("recommendations:detail", args=[rec.pk])).status_code == 404


def test_detail_shows_explanation_from_stored_values(student_client, student, ai_bundle):
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    rec = InternshipRecommendation.objects.filter(run_id=run.run_id, recommendation_rank=1).get()
    page = student_client.get(reverse("recommendations:detail", args=[rec.pk])).content.decode()
    assert rec.recommendation_reason in html.unescape(page) and "72.50%" in page


# --- D-014 embedding cache --------------------------------------------------------------------------------
def test_imported_internships_use_precomputed_vectors(ai_bundle):
    vecs = services.internship_vectors(list(Internship.objects.order_by("embedding_row")), ai_bundle)
    assert ai_bundle.sentence_model.calls == []
    assert np.allclose(vecs, ai_bundle.internship_vecs[:3])


def test_edited_internship_gets_fresh_embedding(ai_bundle):
    i = Internship.objects.get(source_id="T1")
    i.required_skills = ["python", "sql", "excel"]
    i.save()
    services.internship_vectors([i], ai_bundle)
    services.internship_vectors([i], ai_bundle)                      # second call hits the stored embedding
    i.refresh_from_db()
    assert len(ai_bundle.sentence_model.calls) == 1
    assert i.embedding_text_hash == i.text_hash() and len(i.embedding) == 384


def test_new_internship_scored_without_refit(student, ai_bundle):
    _profile(student)
    _qualify(student)
    Internship.objects.create(company_name="New Co", internship_title="Python Developer", job_role="Developer",
                              description="Write Python services.", required_skills=["python"], location="Pune",
                              application_deadline=timezone.localdate() + timedelta(days=10))
    before = dict(ai_bundle.vectorizer.vocabulary_)
    run = services.generate_recommendations(student)
    assert dict(ai_bundle.vectorizer.vocabulary_) == before
    assert any(r.internship.internship_title == "Python Developer" for r in run.eligible)


# --- job-role prediction (career skills only, D-022) ---------------------------------------------------------
def test_prediction_saved_with_model_name_version_scope_and_top_features(student, ai_bundle):
    _profile(student)
    pred, message = services.predict_job_role(student)
    assert message is None and isinstance(pred, JobRolePrediction)
    assert pred.model_name == "RandomForestClassifier" and pred.model_version == "1"
    assert pred.known_skills == ["machine learning", "python", "statistics"]
    assert pred.scope_status in {"confident", "low_confidence"} and pred.top_features


def test_prediction_uses_only_career_skills(student, ai_bundle):
    # free-text skills are web skills; career skills are data skills -> the prediction follows career skills
    _profile(student, skills=["html", "css", "javascript"], career_skills=["machine learning", "python", "statistics"])
    pred, _ = services.predict_job_role(student)
    assert pred.predicted_job_role == "Data Science"
    assert "html" not in pred.known_skills


def test_prediction_without_career_skills_asks_for_them(student_client, student, ai_bundle):
    _profile(student, career_skills=[])
    pred, message = services.predict_job_role(student)
    assert pred is None and "Skills the job-role model understands" in message


def test_prediction_view_out_of_scope_message(student_client, student, ai_bundle):
    _profile(student, career_skills=["python"])                           # only 1 known skill (< 3)
    student_client.post(reverse("recommendations:job_role"))
    page = html.unescape(student_client.get(reverse("recommendations:job_role")).content.decode())
    assert "outside what this model covers (6 computer-science career fields)" in page
    assert "Predicted job role" not in page


class _StubModel:
    """A model whose top probability is fixed (fixture) to test the confidence display."""

    def __init__(self, probs, classes):
        self.probs, self.classes_ = np.array([probs]), np.array(classes)

    def predict_proba(self, X):
        return self.probs

    def __getitem__(self, s):
        names = np.array(["skill__machine learning", "skill__python", "skill__statistics"])
        if s == slice(None, -1):
            return type("Pre", (), {"get_feature_names_out": lambda self: names})()
        return type("Clf", (), {"feature_importances_": np.array([0.5, 0.3, 0.2])})()


@pytest.mark.parametrize("top,label,expect", [(0.35, "Low confidence", "35%"), (0.82, "Predicted job role", "82%")])
def test_confidence_display(student_client, student, ai_bundle, top, label, expect):
    rest = (1 - top) / 2
    ai_bundle.best_model = _StubModel([top, rest, rest], ["Data Science", "Development", "Security"])
    _profile(student)
    student_client.post(reverse("recommendations:job_role"))
    page = student_client.get(reverse("recommendations:job_role")).content.decode()
    assert label in page and expect in page
    if top < 0.5:
        assert "Predicted job role" not in page                     # never shown as a confident prediction


def test_related_internships_apply_gates(student, ai_bundle):
    _profile(student)
    _qualify(student)
    ai_bundle.best_model = _StubModel([0.9, 0.05, 0.05], ["Data Science", "Development", "Security"])
    pred, _ = services.predict_job_role(student)
    related = services.related_internships(pred, student)
    assert [i.internship_title for i, _why in related] == ["Data Science"]
    assert "data science" in related[0][1].lower()


def test_analysis_method_llm_when_available(student, ai_bundle, monkeypatch):
    from ml_core.llm_extract import GapResult
    monkeypatch.setattr(services, "ollama_available", lambda cfg, timeout_s=2.0: True)
    monkeypatch.setattr(services, "analyse_gap", lambda *a, **k: GapResult(["python"], ["git"], "llm", "qwen3:4b"))
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    top = InternshipRecommendation.objects.get(run_id=run.run_id, recommendation_rank=1)
    assert top.analysis_method == "llm" and top.explanation["llm_gap"]["missing"] == ["git"]
    assert top.missing_skills == []                                   # score-consistent list stays deterministic
