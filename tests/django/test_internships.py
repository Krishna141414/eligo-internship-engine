"""Internships: loader, admin CRUD, student search and detail gates (spec §§11.4, 12.4, 14)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone

from internships.models import Internship
from students.models import StudentProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def artifacts(fake_artifacts):
    return fake_artifacts


def _internship(**kw):
    base = dict(company_name="Acme (fixture)", internship_title="Data Science", job_role="Data Science",
                description="Data Science internship.", required_qualification="Any Graduate",
                required_skills=["python", "sql"], location="Bangalore", status="ACTIVE",
                stipend="₹ 10,000 /month", duration="3 Months", eligibility_criteria="Any graduate",
                application_deadline=timezone.localdate() + timedelta(days=30))
    base.update(kw)
    return Internship.objects.create(**base)


# --- loader ----------------------------------------------------------------------------------------
def test_load_internships_idempotent(artifacts):
    call_command("load_internships")
    call_command("load_internships")
    assert Internship.objects.count() == 3
    t1 = Internship.objects.get(source_id="T1")
    assert t1.required_skills == ["python", "sql"] and t1.embedding_row == 0 and len(t1.embedding_text_hash) == 64
    assert t1.embedding_text_hash == t1.text_hash()     # notebook text == Django text (D-014)
    assert Internship.objects.get(source_id="T2").work_mode == "Remote"


def test_load_does_not_reactivate_deactivated_rows(artifacts):
    call_command("load_internships")
    Internship.objects.filter(source_id="T1").update(status="INACTIVE")
    call_command("load_internships")
    assert Internship.objects.get(source_id="T1").status == "INACTIVE"


def test_load_refuses_without_manifest(tmp_path, settings):
    settings.ELIGO_ARTIFACTS_DIR = tmp_path
    with pytest.raises(CommandError, match="notebook"):
        call_command("load_internships")


def test_load_refuses_tampered_csv(artifacts):
    with open(artifacts / "data" / "internships_clean.csv", "a", encoding="utf-8") as f:
        f.write("\n")
    with pytest.raises(CommandError):
        call_command("load_internships")


# --- admin CRUD ---------------------------------------------------------------------------------------
VALID = {"company_name": "New Co", "internship_title": "ML Intern", "job_role": "Machine Learning",
         "description": "Build models.", "required_qualification": "Any Graduate", "specialization": "",
         "minimum_academic_percentage": "60", "required_skills": "Python, SQL", "location": "Pune",
         "work_mode": "On-site", "stipend": "₹ 12,000 /month", "duration": "3 Months",
         "eligibility_criteria": "Final-year students", "application_deadline": "2030-01-31", "status": "ACTIVE"}


def test_admin_add_internship_requires_all_spec_fields(admin_client_, artifacts):
    for field in ("company_name", "job_role", "required_qualification", "required_skills", "location",
                  "stipend", "duration", "eligibility_criteria", "application_deadline"):
        data = dict(VALID, **{field: ""})
        resp = admin_client_.post(reverse("internships:admin_add"), data)
        assert resp.status_code == 200, field
    assert Internship.objects.count() == 0
    resp = admin_client_.post(reverse("internships:admin_add"), VALID)
    assert resp.status_code == 302
    i = Internship.objects.get()
    assert i.required_skills == ["python", "sql"] and i.source_id is None and i.stipend_min == 12000


def test_admin_add_rejects_unknown_skill_with_suggestion(admin_client_, artifacts):
    resp = admin_client_.post(reverse("internships:admin_add"), dict(VALID, required_skills="Pythn"))
    html = resp.content.decode()
    assert resp.status_code == 200 and "pythn" in html.lower() and "python" in html


def test_admin_update_internship(admin_client_, artifacts):
    i = _internship()
    resp = admin_client_.post(reverse("internships:admin_edit", args=[i.pk]), dict(VALID, location="Chennai"))
    assert resp.status_code == 302
    i.refresh_from_db()
    assert i.location == "Chennai"


def test_toggle_is_post_only(admin_client_):
    i = _internship()
    assert admin_client_.get(reverse("internships:admin_toggle", args=[i.pk])).status_code == 405
    admin_client_.post(reverse("internships:admin_toggle", args=[i.pk]))
    i.refresh_from_db()
    assert i.status == "INACTIVE"


def test_admin_crud_forbidden_to_students(student_client):
    assert student_client.get(reverse("internships:admin_list")).status_code == 403


# --- student search + detail --------------------------------------------------------------------------
def test_student_search_filters_by_location_and_role(student_client):
    _internship(internship_title="Data Science", job_role="Data Science", location="Bangalore")
    _internship(internship_title="Sales", job_role="Sales", location="Mumbai")
    html = student_client.get(reverse("internships:list"), {"location": "mumbai"}).content.decode()
    assert "Sales" in html and "Data Science" not in html
    html = student_client.get(reverse("internships:list"), {"job_role": "data"}).content.decode()
    assert "Data Science" in html and "Sales" not in html


def test_student_search_by_qualification(student_client):
    _internship(internship_title="Open to graduates", required_qualification="Any Graduate")
    _internship(internship_title="MBA only", required_qualification="MBA")
    html = student_client.get(reverse("internships:list"), {"qualification": "B.Tech"}).content.decode()
    assert "Open to graduates" in html and "MBA only" not in html


def test_inactive_internship_hidden_from_students(student_client):
    i = _internship(internship_title="Hidden role", status="INACTIVE")
    assert "Hidden role" not in student_client.get(reverse("internships:list")).content.decode()
    assert student_client.get(reverse("internships:detail", args=[i.pk])).status_code == 404


def test_detail_shows_failed_gate_reason(student_client, student):
    StudentProfile.objects.create(student=student, qualification="Diploma", academic_percentage=Decimal("70"),
                                  skills=["python"])
    i = _internship(required_qualification="B.Tech")
    html = student_client.get(reverse("internships:detail", args=[i.pk])).content.decode()
    assert "Requires B.Tech; your qualification is Diploma." in html
    assert "You haven&#x27;t passed an assessment" in html or "You haven't passed an assessment" in html


def test_detail_prompts_for_profile_when_missing(student_client):
    i = _internship()
    html = student_client.get(reverse("internships:detail", args=[i.pk])).content.decode()
    assert "Complete your profile" in html
