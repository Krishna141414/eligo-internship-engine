"""Signature components render from real values (BUILD_PROMPT 5.4; D-023). Fixtures only."""
import json
import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from assessments import services as exam_services
from assessments.models import Assessment, Attempt, Question
from recommendations import services
from recommendations.models import InternshipRecommendation
from students.models import StudentProfile

pytestmark = pytest.mark.django_db


def _profile(student, **kw):
    base = dict(qualification="B.Tech", specialization="CSE", academic_percentage=Decimal("75"), skills=["python", "sql"],
                career_skills=["machine learning", "python", "statistics"])
    base.update(kw)
    return StudentProfile.objects.create(student=student, **base)


def _assessment(n=5, minutes=10):
    a = Assessment.objects.create(assessment_name="Aptitude (fixture)", qualification="Any Graduate",
                                  duration_minutes=minutes, status="ACTIVE")
    for i in range(n):
        Question.objects.create(assessment=a, question_text=f"Q{i}?", option_a="a", option_b="b", option_c="c",
                                option_d="d", correct_option="A")
    return a


def _qualify(student, score="80"):
    a = _assessment()
    now = timezone.now()
    return Attempt.objects.create(student=student, assessment=a, start_time=now - timedelta(minutes=5), deadline=now,
                                  submission_time=now, status="SUBMITTED", total_marks=5, obtained_marks=4,
                                  score_percentage=Decimal(score), result="QUALIFIED")


def test_dashboard_journey_and_stat_band(student_client, student):
    _profile(student)
    html = student_client.get(reverse("students:dashboard")).content.decode()
    states = re.findall(r'class="journey__step" data-state="(\w+)"', html)
    assert states == ["done", "current", "pending", "pending", "pending"]
    assert 'class="stat-band"' in html and "<dt>" in html


def test_recommendation_card_parts(student_client, student, ai_bundle):
    _profile(student)
    _qualify(student)
    run = services.generate_recommendations(student)
    top = run.eligible[0]
    html = student_client.get(reverse("recommendations:list")).content.decode()
    assert f'style="--value: {round(top.final_match_score * 100)}"' in html          # score ring from the real score
    widths = [float(w) for w in re.findall(r'breakdown__seg--\w+" style="width: ([\d.]+)%"', html)[:3]]
    assert sum(widths) == pytest.approx(top.final_match_score * 100, abs=0.05)       # bar = real contributions
    assert html.count('class="chip chip--matched"') >= len(top.matched_skills)
    assert "<details" in html and "Explain this match" in html
    assert 'data-busy="busy-generate"' in html and "Analysing your profile" in html


def test_missing_skill_chip_is_dashed_and_labelled(student_client, student, ai_bundle):
    _profile(student, skills=["python"])
    _qualify(student)
    services.generate_recommendations(student)
    html = student_client.get(reverse("recommendations:list")).content.decode()
    assert 'class="chip chip--missing"' in html and "Missing:" in html


def test_exam_screen_timer_pill_and_palette(student_client, student):
    _profile(student)
    a = _assessment(n=5)
    url = student_client.post(reverse("assessments:start", args=[a.pk])).url
    html = student_client.get(url).content.decode()
    assert 'class="timer-pill"' in html and 'data-remaining="' in html
    assert len(re.findall(r'class="palette__btn"', html)) == 5
    assert 'id="confirm-submit"' in html                                              # confirm modal


def test_result_ring_marks_the_60_percent_threshold(student_client, student):
    _profile(student)
    a = _assessment(n=5)
    attempt = exam_services.start_or_resume(student, a, timezone.now())
    exam_services.submit(attempt.pk, student, {q.pk: "A" for q in a.questions.all()[:3]}, timezone.now())
    html = student_client.get(reverse("assessments:result", args=[attempt.pk])).content.decode()
    assert 'style="--value: 60; --mark: 60"' in html and "Not qualified" in html


def test_job_role_chart_data_from_prediction(student_client, student, ai_bundle):
    _profile(student)
    student_client.post(reverse("recommendations:job_role"))
    html = student_client.get(reverse("recommendations:job_role")).content.decode()
    data = json.loads(re.search(r'<script id="role-chart-data" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert set(data["labels"]) == {"Data Science", "Development", "Security"}
    assert sum(data["values"]) == pytest.approx(100, abs=0.5)


def test_internship_search_empty_state(student_client, student):
    _profile(student)
    html = student_client.get(reverse("internships:list"), {"location": "Atlantis"}).content.decode()
    assert 'class="empty"' in html and "Clear filters" in html


def test_profile_career_skill_picker(student_client, student, fake_artifacts):
    html = student_client.get(reverse("students:profile_edit")).content.decode()
    assert 'data-skill-picker' in html and 'data-skill-filter' in html


# --- admin ------------------------------------------------------------------------------------------
def _chart(html, script_id):
    m = re.search(rf'<script id="{script_id}" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def test_admin_dashboard_outcome_bar_from_counts(admin_client_, student, other_student, make_user):
    make_user(email="third@example.com")                       # never attempted
    _qualify(student)
    _qualify(other_student, score="60.00")
    Attempt.objects.filter(student=other_student).update(result="NOT_QUALIFIED")
    html = admin_client_.get(reverse("adminpanel:dashboard")).content.decode()
    assert 'class="stat-band"' in html
    widths = dict(re.findall(r'outcome__seg--([\w-]+)" style="width: ([\d.]+)%"', html))
    assert widths == {"qualified": "33.33", "not-qualified": "33.33", "not-attempted": "33.33"}


def test_recommendations_per_internship_chart_counts_rows(admin_client_, student, ai_bundle):
    from adminpanel.services import recommendations_per_internship
    _profile(student)
    _qualify(student)
    services.generate_recommendations(student)
    services.generate_recommendations(student)                 # second run: every count doubles
    expected = recommendations_per_internship()
    assert expected and all(n == 2 for _, n in expected)
    assert all(" @ " in label for label, _ in expected)        # "Title @ Company" (Phase 6.5)
    html = admin_client_.get(reverse("adminpanel:dashboard")).content.decode()
    assert _chart(html, "recs-chart-data") is None and "Not enough data yet" in html   # 2 runs, equal counts


def test_ml_comparison_chart_from_saved_metrics(admin_client_, fake_artifacts):
    metrics = {"best_model": "RandomForestClassifier", "selection_rule": "highest macro F1",
               "models": {"DecisionTreeClassifier": {"accuracy": 0.61, "f1_macro": 0.55},
                          "RandomForestClassifier": {"accuracy": 0.68, "f1_macro": 0.62}}}
    (fake_artifacts / "metrics" / "metrics.json").write_text(json.dumps(metrics))
    services.reset_bundle_cache()
    data = _chart(admin_client_.get(reverse("adminpanel:ml")).content.decode(), "ml-chart-data")
    assert data == {"labels": ["DecisionTreeClassifier", "RandomForestClassifier"],
                    "accuracy": [61.0, 68.0], "f1_macro": [55.0, 62.0]}
