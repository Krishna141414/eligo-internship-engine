"""Assessment engine (PLAN Task 15). This module starts with the score lookup the eligibility
gates need; the exam workflow is added in Task 15."""
from __future__ import annotations

from decimal import Decimal

from assessments.models import Attempt
from ml_core.eligibility import QUALIFICATION_HIERARCHY

FINISHED = (Attempt.Status.SUBMITTED, Attempt.Status.AUTO_SUBMITTED)


def _matching(student, qualification: str):
    """Finished attempts on assessments the student's qualification satisfies."""
    open_to = [req for req, accepted in QUALIFICATION_HIERARCHY.items() if qualification in accepted]
    return (Attempt.objects.filter(student=student, status__in=FINISHED, assessment__qualification__in=open_to)
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
