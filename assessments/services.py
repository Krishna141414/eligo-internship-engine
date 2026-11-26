"""Assessment engine: server-enforced timing, grading with Decimal, no duplicate submissions.

Rules enforced here: score % = obtained / total × 100 with Decimal, strictly > 60 qualifies
(1, 2); correct answers never reach the exam page (8); the deadline is enforced on the server, the JS
timer is display only (9); duplicate submissions are rejected with an atomic conditional UPDATE, which
is what actually serialises on SQLite where select_for_update() is a no-op (10, D-011); attempts are
never deleted or overwritten (12).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone

from assessments.models import OPTIONS, Answer, Assessment, Attempt, Question
from ml_core.eligibility import QUALIFICATION_HIERARCHY, is_qualified, score_percentage

FINISHED = (Attempt.Status.SUBMITTED, Attempt.Status.AUTO_SUBMITTED)
VALID_OPTIONS = {o for o, _ in OPTIONS}
SCORE_PLACES = Decimal("0.00000001")   # storage precision of Attempt.score_percentage


class AnswerError(ValueError):
    """Invalid option, or a question that isn't part of this attempt's assessment."""


def _grace() -> timedelta:
    return timedelta(seconds=getattr(settings, "ELIGO_EXAM_GRACE_SECONDS", 10))


def _open_to(qualification: str) -> list[str]:
    return [req for req, accepted in QUALIFICATION_HIERARCHY.items() if qualification in accepted]


# --- availability -----------------------------------------------------------------------------------
def available_assessments(qualification: str):
    """Active assessments the given qualification satisfies, with at least one question."""
    if not qualification:
        return Assessment.objects.none()
    return (Assessment.objects.filter(status=Assessment.Status.ACTIVE, qualification__in=_open_to(qualification))
            .annotate(n_questions=Count("questions")).filter(n_questions__gt=0).order_by("assessment_name"))


def _matching(student, qualification: str):
    """Finished attempts on assessments the student's qualification satisfies."""
    return (Attempt.objects.filter(student=student, status__in=FINISHED, assessment__qualification__in=_open_to(qualification))
            .select_related("assessment").order_by("-submission_time", "-pk"))


def latest_qualifying_attempt(student, qualification: str) -> Attempt | None:
    """Most recent finished attempt scoring strictly above 60% for a matching assessment."""
    return _matching(student, qualification).filter(result=Attempt.Result.QUALIFIED).first()


def score_for_gates(student, qualification: str) -> tuple[Decimal | None, Attempt | None]:
    """Score fed to the assessment gate: the latest qualifying attempt if any, otherwise the latest
    matching attempt (so the reason can show the real score), otherwise None."""
    attempt = latest_qualifying_attempt(student, qualification) or _matching(student, qualification).first()
    if attempt is None or attempt.score_percentage is None:
        return None, attempt
    return Decimal(attempt.score_percentage), attempt


# --- exam workflow -------------------------------------------------------------------------------------
def remaining_seconds(attempt: Attempt, now) -> int:
    return max(0, int((attempt.deadline - now).total_seconds()))


def start_or_resume(student, assessment: Assessment, now) -> Attempt:
    """Resume the student's In_Progress attempt (finalising it first if its time is up), else start one."""
    current = Attempt.objects.filter(student=student, assessment=assessment, status=Attempt.Status.IN_PROGRESS).first()
    if current is not None and not finalise_if_expired(current, now):
        return current
    try:
        with transaction.atomic():
            return Attempt.objects.create(
                student=student, assessment=assessment, start_time=now,
                deadline=now + timedelta(minutes=assessment.duration_minutes),
                total_marks=assessment.total_marks())
    except IntegrityError:   # a parallel request created it first (one_in_progress_attempt constraint)
        return Attempt.objects.get(student=student, assessment=assessment, status=Attempt.Status.IN_PROGRESS)


def exam_questions(attempt: Attempt) -> list[dict]:
    """Questions for the exam page. Built with .values() that never includes correct_option."""
    saved = dict(attempt.answers.values_list("question_id", "selected_option"))
    rows = list(Question.objects.filter(assessment_id=attempt.assessment_id).order_by("id")
                .values("id", "question_text", "option_a", "option_b", "option_c", "option_d", "marks"))
    for number, row in enumerate(rows, start=1):
        row["number"] = number
        row["selected"] = saved.get(row["id"])
    return rows


def _validate(attempt: Attempt, question_id, option) -> tuple[int, str | None]:
    try:
        qid = int(question_id)
    except (TypeError, ValueError) as exc:
        raise AnswerError("Unknown question.") from exc
    option = (option or "").strip().upper() or None
    if option is not None and option not in VALID_OPTIONS:
        raise AnswerError("Choose one of A, B, C or D.")
    if not Question.objects.filter(pk=qid, assessment_id=attempt.assessment_id).exists():
        raise AnswerError("That question isn't part of this assessment.")
    return qid, option


def save_answer(attempt: Attempt, question_id, option, now) -> bool:
    """Autosave one answer. Returns False (nothing saved) if the attempt is finished or time is up."""
    qid, option = _validate(attempt, question_id, option)
    if attempt.status != Attempt.Status.IN_PROGRESS or now > attempt.deadline:
        return False
    Answer.objects.update_or_create(attempt=attempt, question_id=qid, defaults={"selected_option": option})
    return True


@dataclass
class SubmitOutcome:
    status: str   # "submitted" | "auto_submitted" | "duplicate"
    attempt: Attempt


class _AlreadyFinished(Exception):
    pass


def submit(attempt_id: int, student, posted: dict, now) -> SubmitOutcome:
    """Grade and finish an attempt exactly once.

    After deadline + grace, posted answers are ignored and only answers saved before the deadline
    count (AUTO_SUBMITTED). Raises Attempt.DoesNotExist for someone else's attempt and AnswerError
    for invalid posted answers.
    """
    try:
        with transaction.atomic():
            attempt = Attempt.objects.select_for_update().select_related("assessment").get(pk=attempt_id, student=student)
            if attempt.status != Attempt.Status.IN_PROGRESS:
                raise _AlreadyFinished
            late = now > attempt.deadline + _grace()
            if not late:
                for qid, option in posted.items():
                    q, opt = _validate(attempt, qid, option)
                    Answer.objects.update_or_create(attempt=attempt, question_id=q, defaults={"selected_option": opt})
            totals = _grade_answers(attempt)
            new_status = Attempt.Status.AUTO_SUBMITTED if late else Attempt.Status.SUBMITTED
            updated = Attempt.objects.filter(pk=attempt.pk, status=Attempt.Status.IN_PROGRESS).update(
                status=new_status, submission_time=now, **totals)
            if updated != 1:          # someone else finished it between our read and our write
                raise _AlreadyFinished
    except _AlreadyFinished:
        return SubmitOutcome("duplicate", Attempt.objects.get(pk=attempt_id, student=student))
    attempt.refresh_from_db()
    return SubmitOutcome("auto_submitted" if late else "submitted", attempt)


def _grade_answers(attempt: Attempt) -> dict:
    """Mark every question (unanswered = 0). Returns the attempt's new score fields."""
    questions = list(Question.objects.filter(assessment_id=attempt.assessment_id).order_by("id"))
    answers = {a.question_id: a for a in attempt.answers.all()}
    total, obtained = Decimal("0"), Decimal("0")
    for q in questions:
        total += q.marks
        a = answers.get(q.pk) or Answer(attempt=attempt, question=q, selected_option=None)
        a.correct_option = q.correct_option
        a.is_correct = a.selected_option == q.correct_option
        a.marks_obtained = q.marks if a.is_correct else Decimal("0")
        obtained += a.marks_obtained
        a.save()
    score = score_percentage(obtained, total)          # unrounded; ValueError if total is 0
    result = Attempt.Result.QUALIFIED if is_qualified(score) else Attempt.Result.NOT_QUALIFIED
    return {"total_marks": total, "obtained_marks": obtained,
            "score_percentage": score.quantize(SCORE_PLACES), "result": result}


def finalise_if_expired(attempt: Attempt, now) -> bool:
    """Lazy auto-submit: an In_Progress attempt past deadline + grace is graded on its saved answers."""
    if attempt.status == Attempt.Status.IN_PROGRESS and now > attempt.deadline + _grace():
        submit(attempt.pk, attempt.student, {}, now)
        return True
    return False


def finalise_expired_for(student, now=None) -> int:
    now = now or timezone.now()
    n = 0
    for attempt in Attempt.objects.filter(student=student, status=Attempt.Status.IN_PROGRESS, deadline__lt=now - _grace()):
        n += finalise_if_expired(attempt, now)
    return n


def can_activate(assessment: Assessment) -> tuple[bool, str]:
    if not assessment.questions.exists():
        return False, "Add at least one question before activating this assessment."
    if assessment.total_marks() <= 0:
        return False, "Total marks must be more than 0 before activating this assessment."
    return True, ""
