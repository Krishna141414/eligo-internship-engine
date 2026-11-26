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


def test_not_eligible_preview_groups_repeated_listings(student_client, student, ai_bundle):
    """Phase 6.5: the same title at the same company with the same reasons is shown once, with a count."""
    _profile(student, skills=["python", "sql", "excel"])
    _qualify(student)
    mba = Internship.objects.get(internship_title="MBA Strategy Intern")
    for city in ("Pune", "Delhi"):
        mba.pk, mba.source_id, mba.location = None, f"COPY-{city}", city   # dataset rows, like real repeats
        mba.save()
    preview, n_failing = services.ineligible_preview_for(student)
    assert n_failing == 3
    assert [(i.internship_title, i.similar_listings) for i, _ in preview] == [("MBA Strategy Intern", 3)]
    page = student_client.get(reverse("recommendations:list")).content.decode()
    assert page.count("MBA Strategy Intern") == 1 and "3 listings" in page


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
    assert "Data Science" in page and "Rule-based" in page and "Why you can’t apply yet" in page   # curly apostrophe (Phase 7 copy pass)


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


def test_detail_lists_each_eligibility_check_once(student_client, student, ai_bundle):
    """Phase 6.5: the assessment gate was listed twice (6 lines vs "All 5 checks passed" on the card)."""
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    rec = InternshipRecommendation.objects.filter(run_id=run.run_id, recommendation_rank=1).get()
    n_gates = len(rec.explanation["gates"])
    card = student_client.get(reverse("recommendations:list")).content.decode()
    assert f"All {n_gates} eligibility checks passed" in card
    page = student_client.get(reverse("recommendations:detail", args=[rec.pk])).content.decode()
    gate_list = page.split('<ul class="gate-list">', 1)[1].split("</ul>", 1)[0]
    assert gate_list.count("<li") == n_gates


def test_llm_detail_reads_as_one_sentence(student_client, student, ai_bundle, monkeypatch):
    _llm_on(monkeypatch)
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    rec = InternshipRecommendation.objects.filter(run_id=run.run_id, recommendation_rank=1).get()
    student_client.post(reverse("recommendations:second_opinion", args=[rec.pk]))
    page = html.unescape(student_client.get(reverse("recommendations:detail", args=[rec.pk])).content.decode())
    assert "Checked by local LLM (qwen3:4b, prompt v1)." in page and ".)." not in page and "Extracted by" not in page


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


# --- D-025: asynchronous AI second opinion -------------------------------------------------------------------
def _llm_on(monkeypatch, gap=None):
    from ml_core.llm_extract import GapResult
    calls = []

    def fake_gap(*args, **kwargs):
        calls.append(kwargs.get("use_llm"))
        if kwargs.get("use_llm"):
            return gap or GapResult(["python"], ["git"], "llm", "Checked by local LLM (qwen3:4b, prompt v1).")
        return GapResult(["python"], [], "rule_based", "Rule-based extraction (LLM not used).")
    monkeypatch.setattr(services, "ollama_available", lambda cfg, timeout_s=2.0: True)
    monkeypatch.setattr(services, "analyse_gap", fake_gap)
    return calls


def test_generate_never_calls_llm(student, ai_bundle, monkeypatch):
    calls = _llm_on(monkeypatch)
    _profile(student)
    _qualify(student)
    services.generate_recommendations(student)
    assert calls and not any(calls)                       # every gap check during generation is rule-based


def test_top3_marked_pending_when_llm_available(student, ai_bundle, monkeypatch):
    _llm_on(monkeypatch)
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    states = {r.recommendation_rank: r.second_opinion for r in run.eligible}
    assert states == {1: "pending", 2: "pending"}         # fixture has 2 eligible; ranks 1-3 pending
    assert all(r.analysis_method == "rule_based" for r in run.eligible)


def test_second_opinion_unavailable_without_ollama(student, ai_bundle):
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    assert {r.second_opinion for r in run.eligible} == {"unavailable"}


def test_second_opinion_endpoint_updates_row(student_client, student, ai_bundle, monkeypatch):
    _llm_on(monkeypatch)
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    rec = run.eligible[0]
    resp = student_client.post(reverse("recommendations:second_opinion", args=[rec.pk]))
    data = resp.json()
    assert resp.status_code == 200 and data["status"] == "done" and data["missing"] == ["git"]
    rec.refresh_from_db()
    assert rec.second_opinion == "done" and rec.analysis_method == "llm"
    assert rec.explanation["llm_gap"]["missing"] == ["git"]
    assert rec.missing_skills == []                        # score-consistent list stays deterministic (D-024)


def test_second_opinion_falls_back_when_llm_fails(student_client, student, ai_bundle, monkeypatch):
    from ml_core.llm_extract import GapResult
    _llm_on(monkeypatch, gap=GapResult(["python"], [], "rule_based", "Ollama not reachable (ReadTimeout)."))
    _profile(student)
    _qualify(student)
    rec = services.generate_recommendations(student).eligible[0]
    data = student_client.post(reverse("recommendations:second_opinion", args=[rec.pk])).json()
    assert data["status"] == "unavailable" and "ReadTimeout" in data["detail"]


def test_second_opinion_is_idempotent(student_client, student, ai_bundle, monkeypatch):
    calls = _llm_on(monkeypatch)
    _profile(student)
    _qualify(student)
    rec = services.generate_recommendations(student).eligible[0]
    url = reverse("recommendations:second_opinion", args=[rec.pk])
    student_client.post(url)
    n = calls.count(True)
    student_client.post(url)
    assert calls.count(True) == n == 1


def test_second_opinion_other_student_404(client, student, other_student, ai_bundle, monkeypatch):
    _llm_on(monkeypatch)
    _profile(student)
    _qualify(student)
    rec = services.generate_recommendations(student).eligible[0]
    client.force_login(other_student)
    assert client.post(reverse("recommendations:second_opinion", args=[rec.pk])).status_code == 404


def test_second_opinion_requires_post(student_client, student, ai_bundle, monkeypatch):
    _llm_on(monkeypatch)
    _profile(student)
    _qualify(student)
    rec = services.generate_recommendations(student).eligible[0]
    assert student_client.get(reverse("recommendations:second_opinion", args=[rec.pk])).status_code == 405


def test_list_page_renders_pending_cards_without_waiting(student_client, student, ai_bundle, monkeypatch):
    _llm_on(monkeypatch)
    _profile(student)
    _qualify(student)
    student_client.post(reverse("recommendations:list"))
    page = html.unescape(student_client.get(reverse("recommendations:list")).content.decode())
    assert "AI second opinion: checking…" in page and 'data-second-opinion-url="' in page
