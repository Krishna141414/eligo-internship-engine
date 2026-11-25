"""seed_demo: idempotent, DEMO-labelled, never touches internships (hard rule 7)."""
import pytest
from django.core.management import call_command

from accounts.models import User
from assessments.models import Assessment, Question
from assessments.services import can_activate
from internships.models import Internship
from ml_core.demo import DEMO_PROFILES
from students.models import StudentProfile

pytestmark = pytest.mark.django_db


def test_seed_demo_idempotent():
    call_command("seed_demo")
    counts = (User.objects.count(), Assessment.objects.count(), Question.objects.count(), StudentProfile.objects.count())
    call_command("seed_demo")
    assert (User.objects.count(), Assessment.objects.count(), Question.objects.count(),
            StudentProfile.objects.count()) == counts
    assert counts[0] == len(DEMO_PROFILES)


def test_all_demo_objects_labelled():
    call_command("seed_demo")
    assert all(u.name.startswith("DEMO") and u.email.endswith("@eligo.local") for u in User.objects.all())
    assert all(a.assessment_name.startswith("DEMO") for a in Assessment.objects.all())


def test_demo_assessments_are_activatable_and_timed():
    call_command("seed_demo")
    by_name = {a.assessment_name: a for a in Assessment.objects.all()}
    assert by_name["DEMO – 1-minute timer check"].duration_minutes == 1
    assert by_name["DEMO – B.Tech/B.E. aptitude"].duration_minutes == 2
    assert by_name["DEMO – B.Tech/B.E. aptitude"].questions.count() == 10
    assert all(a.status == "ACTIVE" and can_activate(a)[0] for a in by_name.values())


def test_demo_profiles_match_shared_definition():
    call_command("seed_demo")
    cs = DEMO_PROFILES["cs"]
    p = StudentProfile.objects.get(student__name=cs.label)
    assert p.career_skills == sorted(cs.career_skills) and p.qualification == cs.qualification
    assert p.skills                                     # free-text skills normalised for matching


def test_seed_demo_never_touches_internships():
    Internship.objects.create(company_name="Keep", internship_title="Keep", job_role="Keep", description="d", location="L")
    call_command("seed_demo")
    assert Internship.objects.count() == 1
