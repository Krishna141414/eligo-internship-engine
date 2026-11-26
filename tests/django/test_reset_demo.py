"""reset_demo: wipes DEMO students' attempts, recommendations and predictions, removes test accounts
(E2E runs, rehearsals), restores the DEMO accounts, and never touches real students or admins (D-028)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.forms.models import model_to_dict
from django.utils import timezone

from accounts.models import User
from assessments.models import Answer, Assessment, Attempt, Question
from internships.models import Internship
from ml_core.demo import DEMO_PROFILES
from recommendations.management.commands.seed_demo import DEFAULT_PASSWORD, demo_email
from recommendations.models import InternshipRecommendation, JobRolePrediction
from students.models import StudentProfile

pytestmark = pytest.mark.django_db


def _history(user, assessment, internship):
    """One finished attempt (with answers), one recommendation and one prediction for `user`."""
    now = timezone.now()
    attempt = Attempt.objects.create(student=user, assessment=assessment, start_time=now - timedelta(minutes=5),
                                     deadline=now, submission_time=now, status="SUBMITTED", total_marks=1,
                                     obtained_marks=1, score_percentage=Decimal("100"), result="QUALIFIED")
    Answer.objects.create(attempt=attempt, question=assessment.questions.first(), selected_option="A",
                          correct_option="A", is_correct=True, marks_obtained=Decimal("1"))
    InternshipRecommendation.objects.create(
        student=user, internship=internship, assessment_attempt=attempt, skill_match_score=1, content_similarity_score=0.5,
        semantic_similarity_score=0.5, final_match_score=0.6, recommendation_rank=1, recommendation_reason="fixture")
    JobRolePrediction.objects.create(student=user, predicted_job_role="Data Science", probability=0.9,
                                     scope_status="confident", model_name="RF", model_version="1")


def _snapshot(user):
    rows = [model_to_dict(user, exclude=["last_login"])]
    for qs in (Attempt.objects.filter(student=user), Answer.objects.filter(attempt__student=user),
               InternshipRecommendation.objects.filter(student=user), JobRolePrediction.objects.filter(student=user),
               StudentProfile.objects.filter(student=user)):
        rows += [model_to_dict(o) for o in qs.order_by("pk")]
    return rows


@pytest.fixture
def world(make_user, admin_user):
    call_command("seed_demo")
    # a real student on a normal domain (fixture values, never contacted)
    student = make_user(email="riya.sharma@college.ac.in", name="Riya Sharma (fixture)")
    internship = Internship.objects.create(company_name="Real Co (fixture)", internship_title="Analyst", job_role="Analyst",
                                           description="d", location="Delhi")
    real_exam = Assessment.objects.create(assessment_name="Real aptitude (fixture)", qualification="Any Graduate",
                                          duration_minutes=10, status="ACTIVE")
    Question.objects.create(assessment=real_exam, question_text="Q?", option_a="a", option_b="b", option_c="c",
                            option_d="d", correct_option="A")
    StudentProfile.objects.create(student=student, qualification="B.Sc", academic_percentage=Decimal("70"), skills=["sql"])
    _history(student, real_exam, internship)                          # a real student's history

    # test accounts: the Phase 6 E2E account, a reserved .test domain, and a DEMO-named rehearsal account
    tests = [make_user(email="e2e.check@example.com", name="DEMO – E2E check student"),
             make_user(email="playwright@runner.test", name="Playwright runner"),
             make_user(email="rehearsal.cs@gmail.com", name="DEMO – rehearsal")]
    for t in tests:
        StudentProfile.objects.create(student=t, qualification="B.Tech", academic_percentage=Decimal("70"), skills=["sql"])
        _history(t, real_exam, internship)

    demo = User.objects.get(email=demo_email("cs"))
    demo_exam = Assessment.objects.get(assessment_name="DEMO – B.Tech/B.E. aptitude")
    _history(demo, demo_exam, internship)
    _history(demo, real_exam, internship)                             # DEMO student also took a real exam
    demo.name, demo.status = "Renamed during the demo", User.Status.INACTIVE
    demo.set_password("changed-in-demo")
    demo.save()
    StudentProfile.objects.filter(student=demo).update(college_name="edited", skills=["excel"])
    demo_exam.status = Assessment.Status.INACTIVE
    demo_exam.save(update_fields=["status"])
    return {"real": student, "admin": admin_user, "demo": demo, "internship": internship, "real_exam": real_exam,
            "tests": tests}


def test_reset_demo_never_touches_non_demo_data(world):
    real, admin = world["real"], world["admin"]
    before = (_snapshot(real), _snapshot(admin), [model_to_dict(world["internship"])],
              model_to_dict(world["real_exam"]), list(world["real_exam"].questions.values()))
    call_command("reset_demo")
    world["internship"].refresh_from_db()
    world["real_exam"].refresh_from_db()
    after = (_snapshot(real), _snapshot(admin), [model_to_dict(world["internship"])],
             model_to_dict(world["real_exam"]), list(world["real_exam"].questions.values()))
    assert after == before
    assert Attempt.objects.filter(student=real).count() == 1


def test_reset_demo_leaves_demo_accounts_clean_and_ready(world, client):
    call_command("reset_demo")
    demo_users = User.objects.filter(email__in=[demo_email(k) for k in DEMO_PROFILES])
    assert demo_users.count() == len(DEMO_PROFILES)
    for model in (Attempt, InternshipRecommendation, JobRolePrediction):
        assert not model.objects.filter(student__in=demo_users).exists(), model.__name__
    assert not Answer.objects.filter(attempt__student__in=demo_users).exists()
    demo = User.objects.get(pk=world["demo"].pk)
    assert demo.name == DEMO_PROFILES["cs"].label and demo.status == User.Status.ACTIVE and demo.is_active
    assert client.login(username=demo.email, password=DEFAULT_PASSWORD)
    profile = StudentProfile.objects.get(student=demo)
    assert profile.college_name == DEMO_PROFILES["cs"].college_name and profile.career_skills
    assert all(a.status == "ACTIVE" for a in Assessment.objects.filter(assessment_name__startswith="DEMO"))


def test_reset_demo_removes_test_accounts_and_keeps_admins(world):
    call_command("reset_demo")
    removed = [t.pk for t in world["tests"]]
    assert not User.objects.filter(pk__in=removed).exists()
    for model in (Attempt, InternshipRecommendation, JobRolePrediction, StudentProfile):
        assert not model.objects.filter(student_id__in=removed).exists(), model.__name__
    students = set(User.objects.filter(user_type=User.UserType.STUDENT).values_list("email", flat=True))
    assert students == {demo_email(k) for k in DEMO_PROFILES} | {world["real"].email}
    assert User.objects.filter(pk=world["admin"].pk).exists()           # admin@example.com is never removed


def test_reset_demo_on_empty_database_just_seeds():
    call_command("reset_demo")
    assert User.objects.filter(email__in=[demo_email(k) for k in DEMO_PROFILES]).count() == len(DEMO_PROFILES)
