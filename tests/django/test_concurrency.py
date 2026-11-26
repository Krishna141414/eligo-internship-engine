"""Two submits of the same attempt at the same moment: exactly one grades it, the other is told it's a
duplicate, and nothing crashes (hard rule 10, D-011). Real threads, real SQLite file locking."""
import threading

import pytest
from django.db import connection
from django.utils import timezone

from assessments import services
from assessments.models import Answer, Assessment, Attempt, Question

ROUNDS = 6


def _assessment(i):
    a = Assessment.objects.create(assessment_name=f"Race (fixture) {i}", qualification="Any Graduate",
                                  duration_minutes=10, status="ACTIVE")
    for n in range(4):
        Question.objects.create(assessment=a, question_text=f"Q{n}?", option_a="a", option_b="b", option_c="c",
                                option_d="d", correct_option="A")
    return a


def _race(attempt_id, student, posted):
    barrier = threading.Barrier(2)
    outcomes, errors = [], []

    def worker():
        try:
            barrier.wait()
            outcomes.append(services.submit(attempt_id, student, posted, timezone.now()).status)
        except Exception as exc:  # noqa: BLE001 - any exception is the failure we're looking for
            errors.append(repr(exc))
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return outcomes, errors


@pytest.mark.django_db(transaction=True)
def test_parallel_submits_only_one_wins(student):
    for i in range(ROUNDS):
        a = _assessment(i)
        attempt = services.start_or_resume(student, a, timezone.now())
        posted = {str(q.pk): "A" for q in a.questions.all()}
        outcomes, errors = _race(attempt.pk, student, posted)
        assert errors == [], f"round {i}: {errors}"
        assert sorted(outcomes) == ["duplicate", "submitted"], f"round {i}: {outcomes}"
        attempt.refresh_from_db()
        assert attempt.status == Attempt.Status.SUBMITTED and attempt.score_percentage == 100
        assert Answer.objects.filter(attempt=attempt).count() == 4        # graded once, no duplicate rows
