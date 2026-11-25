"""Domain models: constraints, validators, history protection (spec §10, rules 10 and 12)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from assessments.models import Answer, Assessment, Attempt, Question
from internships.models import Internship
from students.models import StudentProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def assessment():
    a = Assessment.objects.create(assessment_name="Aptitude (test fixture)", qualification="Any Graduate",
                                  duration_minutes=10, status="ACTIVE")
    Question.objects.create(assessment=a, question_text="2+2?", option_a="3", option_b="4", option_c="5",
                            option_d="6", correct_option="B", marks=Decimal("1"))
    return a


def _attempt(student, assessment, status="IN_PROGRESS"):
    now = timezone.now()
    return Attempt.objects.create(student=student, assessment=assessment, start_time=now,
                                  deadline=now + timedelta(minutes=assessment.duration_minutes), status=status)


def test_second_in_progress_attempt_violates_constraint(student, assessment):
    _attempt(student, assessment)
    with pytest.raises(IntegrityError), transaction.atomic():
        _attempt(student, assessment)


def test_two_submitted_attempts_allowed(student, assessment):
    _attempt(student, assessment, "SUBMITTED")
    _attempt(student, assessment, "SUBMITTED")
    _attempt(student, assessment)   # plus one in progress
    assert Attempt.objects.filter(student=student).count() == 3


def test_answer_unique_per_question(student, assessment):
    attempt = _attempt(student, assessment)
    q = assessment.questions.first()
    Answer.objects.create(attempt=attempt, question=q, selected_option="B")
    with pytest.raises(IntegrityError), transaction.atomic():
        Answer.objects.create(attempt=attempt, question=q, selected_option="A")


def test_correct_option_validator_rejects_E(assessment):
    q = Question(assessment=assessment, question_text="?", option_a="a", option_b="b", option_c="c",
                 option_d="d", correct_option="E", marks=Decimal("1"))
    with pytest.raises(ValidationError):
        q.full_clean()


def test_negative_marks_rejected(assessment):
    q = Question(assessment=assessment, question_text="?", option_a="a", option_b="b", option_c="c",
                 option_d="d", correct_option="A", marks=Decimal("-1"))
    with pytest.raises(ValidationError):
        q.full_clean()


def test_percentage_validator_rejects_101(student):
    p = StudentProfile(student=student, qualification="B.Tech", academic_percentage=Decimal("101"))
    with pytest.raises(ValidationError):
        p.full_clean()


def test_question_with_answers_cannot_be_deleted(student, assessment):
    attempt = _attempt(student, assessment)
    q = assessment.questions.first()
    Answer.objects.create(attempt=attempt, question=q, selected_option="B")
    with pytest.raises(ProtectedError):
        q.delete()


def test_assessment_with_attempts_cannot_be_deleted(student, assessment):
    _attempt(student, assessment, "SUBMITTED")
    with pytest.raises(ProtectedError):
        assessment.delete()


def _internship(**kw):
    base = dict(company_name="Acme (fixture)", internship_title="Data Science", job_role="Data Science",
                description="Data Science internship at Acme.", required_qualification="Any Graduate",
                required_skills=["python", "sql"], location="Bangalore", status="ACTIVE")
    base.update(kw)
    return Internship.objects.create(**base)


def test_internship_text_hash_changes_with_skills():
    i = _internship()
    before = i.text_hash()
    i.required_skills = ["python", "sql", "excel"]
    assert i.text_hash() != before and len(before) == 64


def test_internship_text_matches_notebook_definition():
    from ml_core.preprocessing import build_internship_text
    i = _internship()
    assert i.text_for_matching() == build_internship_text("Data Science", "Data Science", ["python", "sql"],
                                                          "", "", "Data Science internship at Acme.")


def test_profile_career_skills_default_empty(student):
    p = StudentProfile.objects.create(student=student)
    assert p.career_skills == [] and p.skills == []
