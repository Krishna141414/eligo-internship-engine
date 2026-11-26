"""Assessment engine: server-timed exam, grading, no answer leakage, no duplicates (spec §§12.5–12.6, 16;
rules 1, 2, 8, 9, 10, 12). Questions are TEST FIXTURES."""
import html
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from assessments import services
from assessments.models import Answer, Assessment, Attempt, Question
from students.models import StudentProfile

pytestmark = pytest.mark.django_db
CORRECT = ["A", "B", "C", "D", "A"]
SECRET = "UNIQUE-CORRECT-OPTION-TEXT"


@pytest.fixture
def assessment():
    a = Assessment.objects.create(assessment_name="Graduate aptitude (fixture)", qualification="Any Graduate",
                                  duration_minutes=10, status="ACTIVE")
    for i, c in enumerate(CORRECT):
        opts = {f"option_{k}": f"option {k} of q{i}" for k in "abcd"}
        opts[f"option_{c.lower()}"] = f"{SECRET} q{i}"
        Question.objects.create(assessment=a, question_text=f"Question {i}?", correct_option=c, marks=Decimal("1"), **opts)
    return a


@pytest.fixture
def profile(student):
    return StudentProfile.objects.create(student=student, qualification="B.Tech", academic_percentage=Decimal("75"),
                                         skills=["python"])


def _qids(a):
    return list(a.questions.values_list("id", flat=True))


def _answers(a, n_correct):
    """Posted answers with exactly n_correct right."""
    out = {}
    for i, qid in enumerate(_qids(a)):
        out[qid] = CORRECT[i] if i < n_correct else ("B" if CORRECT[i] != "B" else "C")
    return out


# --- listing -------------------------------------------------------------------------------------------
def test_students_only_see_matching_qualification_assessments(student_client, profile, assessment):
    Assessment.objects.create(assessment_name="MBA-only (fixture)", qualification="MBA", duration_minutes=5,
                              status="ACTIVE").questions.create(question_text="?", option_a="a", option_b="b",
                                                                option_c="c", option_d="d", correct_option="A")
    html = student_client.get(reverse("assessments:list")).content.decode()
    assert "Graduate aptitude (fixture)" in html and "MBA-only (fixture)" not in html


def test_cannot_start_assessment_for_other_qualification(student_client, profile):
    mba = Assessment.objects.create(assessment_name="MBA-only", qualification="MBA", duration_minutes=5, status="ACTIVE")
    mba.questions.create(question_text="?", option_a="a", option_b="b", option_c="c", option_d="d", correct_option="A")
    assert student_client.post(reverse("assessments:start", args=[mba.pk])).status_code == 404


# --- exam page -----------------------------------------------------------------------------------------
def test_exam_page_has_no_correct_answers(student_client, profile, assessment):
    resp = student_client.post(reverse("assessments:start", args=[assessment.pk]))
    exam = student_client.get(resp.url)
    html = exam.content.decode()
    assert "correct_option" not in html and "data-correct" not in html and "is-correct" not in html
    assert all("correct_option" not in q for q in exam.context["questions"])
    # the option text itself is shown (it's one of four choices) but nothing marks it as the right one
    assert html.count(f"{SECRET} q0") == 1


def test_exam_page_is_never_cached(student_client, profile, assessment):
    """Back after submitting must ask the server (which redirects to the result), never show a stale,
    live-looking exam from the browser cache (found in the Phase 6 E2E run)."""
    url = student_client.post(reverse("assessments:start", args=[assessment.pk])).url
    cache_control = student_client.get(url)["Cache-Control"]
    assert "no-store" in cache_control and "no-cache" in cache_control


def test_resume_returns_same_attempt_and_server_remaining_time(student_client, profile, assessment):
    first = student_client.post(reverse("assessments:start", args=[assessment.pk])).url
    second = student_client.post(reverse("assessments:start", args=[assessment.pk])).url
    assert first == second and Attempt.objects.count() == 1
    remaining = student_client.get(first).context["remaining_seconds"]
    assert 0 < remaining <= 600


# --- grading ---------------------------------------------------------------------------------------------
def _start(student, a, now=None):
    return services.start_or_resume(student, a, now or timezone.now())


def test_grading_decimal_and_threshold(student, profile, assessment):
    at = _start(student, assessment)
    services.submit(at.pk, student, _answers(assessment, 3), timezone.now())
    at.refresh_from_db()
    assert at.score_percentage == Decimal("60") and at.result == "NOT_QUALIFIED"      # exactly 60% fails
    assert at.obtained_marks == Decimal("3") and at.total_marks == Decimal("5")
    at2 = _start(student, assessment)
    services.submit(at2.pk, student, _answers(assessment, 4), timezone.now())
    at2.refresh_from_db()
    assert at2.score_percentage == Decimal("80") and at2.result == "QUALIFIED"


def test_unanswered_count_as_zero(student, profile, assessment):
    at = _start(student, assessment)
    qids = _qids(assessment)
    services.submit(at.pk, student, {qids[0]: CORRECT[0]}, timezone.now())
    at.refresh_from_db()
    assert at.obtained_marks == Decimal("1") and at.score_percentage == Decimal("20")
    assert Answer.objects.filter(attempt=at).count() == 5          # every question recorded
    assert Answer.objects.filter(attempt=at, selected_option__isnull=True).count() == 4


def test_duplicate_submission_rejected(student, profile, assessment):
    at = _start(student, assessment)
    first = services.submit(at.pk, student, _answers(assessment, 4), timezone.now())
    second = services.submit(at.pk, student, _answers(assessment, 5), timezone.now())
    at.refresh_from_db()
    assert first.status == "submitted" and second.status == "duplicate"
    assert at.obtained_marks == Decimal("4")


def test_duplicate_submit_via_view_shows_message(student_client, student, profile, assessment):
    url = student_client.post(reverse("assessments:start", args=[assessment.pk])).url
    at = Attempt.objects.get()
    data = {f"q_{k}": v for k, v in _answers(assessment, 4).items()}
    student_client.post(reverse("assessments:submit", args=[at.pk]), data)
    resp = student_client.post(reverse("assessments:submit", args=[at.pk]), data, follow=True)
    assert "already submitted" in resp.content.decode()


def test_late_submission_auto_submitted_uses_saved_answers_only(student, profile, assessment):
    start = timezone.now() - timedelta(minutes=11)
    at = services.start_or_resume(student, assessment, start)          # deadline = start + 10 min (1 min ago)
    qids = _qids(assessment)
    services.save_answer(at, qids[0], CORRECT[0], start + timedelta(minutes=1))
    services.save_answer(at, qids[1], CORRECT[1], start + timedelta(minutes=2))
    out = services.submit(at.pk, student, _answers(assessment, 5), at.deadline + timedelta(seconds=30))
    at.refresh_from_db()
    assert out.status == "auto_submitted" and at.status == "AUTO_SUBMITTED"
    assert at.obtained_marks == Decimal("2")


def test_submit_within_grace_counts_posted_answers(student, profile, assessment):
    start = timezone.now() - timedelta(minutes=10)
    at = services.start_or_resume(student, assessment, start)
    services.submit(at.pk, student, _answers(assessment, 5), at.deadline + timedelta(seconds=5))
    at.refresh_from_db()
    assert at.status == "SUBMITTED" and at.obtained_marks == Decimal("5")


def test_expired_attempt_finalised_on_page_load(student_client, student, profile, assessment):
    at = services.start_or_resume(student, assessment, timezone.now() - timedelta(minutes=30))
    student_client.get(reverse("assessments:list"))
    at.refresh_from_db()
    assert at.status == "AUTO_SUBMITTED" and at.result == "NOT_QUALIFIED"


def test_save_answer_after_deadline_rejected(student_client, student, profile, assessment):
    at = services.start_or_resume(student, assessment, timezone.now() - timedelta(minutes=11))
    resp = student_client.post(reverse("assessments:save_answer", args=[at.pk]),
                               {"question": _qids(assessment)[0], "option": "A"})
    assert resp.status_code == 409 and not Answer.objects.exists()


def test_save_answer_autosaves(student_client, student, profile, assessment):
    at = _start(student, assessment)
    resp = student_client.post(reverse("assessments:save_answer", args=[at.pk]),
                               {"question": _qids(assessment)[0], "option": "C"})
    assert resp.status_code == 200 and resp.json() == {"saved": True}
    assert Answer.objects.get().selected_option == "C"


def test_invalid_option_or_foreign_question_rejected(student_client, student, profile, assessment):
    at = _start(student, assessment)
    url = reverse("assessments:save_answer", args=[at.pk])
    assert student_client.post(url, {"question": _qids(assessment)[0], "option": "E"}).status_code == 400
    other = Assessment.objects.create(assessment_name="Other", qualification="Any Graduate", duration_minutes=5)
    foreign = other.questions.create(question_text="?", option_a="a", option_b="b", option_c="c", option_d="d",
                                     correct_option="A")
    assert student_client.post(url, {"question": foreign.pk, "option": "A"}).status_code == 400
    assert not Answer.objects.exists()


def test_other_students_attempt_is_404(client, other_student, profile, assessment, student):
    at = _start(student, assessment)
    client.force_login(other_student)
    assert client.get(reverse("assessments:exam", args=[at.pk])).status_code == 404
    assert client.post(reverse("assessments:submit", args=[at.pk])).status_code == 404
    services.submit(at.pk, student, {}, timezone.now())
    assert client.get(reverse("assessments:result", args=[at.pk])).status_code == 404


def test_result_page_shows_required_stats(student_client, student, profile, assessment):
    at = _start(student, assessment)
    services.submit(at.pk, student, _answers(assessment, 4), timezone.now())
    html = student_client.get(reverse("assessments:result", args=[at.pk])).content.decode()
    for text in ("5", "4", "80.00%", "Qualified"):
        assert text in html


def test_retake_creates_new_attempt_and_keeps_history(student, profile, assessment):
    first = _start(student, assessment)
    services.submit(first.pk, student, _answers(assessment, 2), timezone.now())
    second = _start(student, assessment)
    assert second.pk != first.pk and Attempt.objects.filter(student=student).count() == 2
    first.refresh_from_db()
    assert first.score_percentage == Decimal("40")


# --- admin ----------------------------------------------------------------------------------------------
def test_cannot_activate_assessment_without_questions(admin_client_):
    a = Assessment.objects.create(assessment_name="Empty", qualification="Any Graduate", duration_minutes=5)
    resp = admin_client_.post(reverse("assessments:admin_toggle", args=[a.pk]), follow=True)
    a.refresh_from_db()
    assert a.status == "INACTIVE" and "Add at least one question before activating" in resp.content.decode()


def test_admin_creates_assessment_and_adds_mcq(admin_client_):
    resp = admin_client_.post(reverse("assessments:admin_add"), {
        "assessment_name": "New test", "qualification": "Any Graduate", "specialization": "", "duration_minutes": 15})
    a = Assessment.objects.get()
    assert resp.status_code == 302 and a.status == "INACTIVE"
    resp = admin_client_.post(reverse("assessments:question_add", args=[a.pk]), {
        "question_text": "Capital of India?", "option_a": "Delhi", "option_b": "Mumbai", "option_c": "Pune",
        "option_d": "Agra", "correct_option": "A", "marks": "2"})
    assert resp.status_code == 302 and a.questions.count() == 1
    admin_client_.post(reverse("assessments:admin_toggle", args=[a.pk]))
    a.refresh_from_db()
    assert a.status == "ACTIVE"


def test_admin_cannot_delete_answered_question(admin_client_, student, profile, assessment):
    at = _start(student, assessment)
    services.submit(at.pk, student, _answers(assessment, 1), timezone.now())
    q = assessment.questions.first()
    resp = admin_client_.post(reverse("assessments:question_delete", args=[q.pk]), follow=True)
    assert Question.objects.filter(pk=q.pk).exists()
    assert "can't be deleted" in html.unescape(resp.content.decode())


def test_admin_assessment_pages_forbidden_to_students(student_client):
    assert student_client.get(reverse("assessments:admin_list")).status_code == 403
