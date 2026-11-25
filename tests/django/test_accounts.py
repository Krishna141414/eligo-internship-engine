"""Accounts: custom user, email login, registration, roles, inactive users (spec §§10, 11.1, 12.1, 16)."""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_register_creates_student_with_hashed_password(client):
    resp = client.post(reverse("accounts:register"), {
        "name": "New Student", "email": "New.Student@Example.com", "mobile_number": "9123456789",
        "password1": PASSWORD, "password2": PASSWORD})
    assert resp.status_code == 302
    user = get_user_model().objects.get(email="new.student@example.com")
    assert user.user_type == "STUDENT" and user.status == "ACTIVE"
    assert user.password != PASSWORD and user.check_password(PASSWORD)


def test_register_rejects_duplicate_email_case_insensitive(client, student):
    resp = client.post(reverse("accounts:register"), {
        "name": "Dup", "email": "STUDENT@example.com", "mobile_number": "9123456789",
        "password1": PASSWORD, "password2": PASSWORD})
    assert resp.status_code == 200 and get_user_model().objects.count() == 1


def test_register_rejects_bad_mobile(client):
    resp = client.post(reverse("accounts:register"), {
        "name": "X", "email": "x@example.com", "mobile_number": "12345",
        "password1": PASSWORD, "password2": PASSWORD})
    assert resp.status_code == 200 and "10-digit" in resp.content.decode()


def test_login_by_email(client, student):
    resp = client.post(reverse("accounts:login"), {"username": "Student@Example.com", "password": PASSWORD})
    assert resp.status_code == 302
    assert client.session.get("_auth_user_id") == str(student.pk)


def test_inactive_user_cannot_login_with_message(client, make_user):
    make_user(email="sleepy@example.com", status="INACTIVE")
    resp = client.post(reverse("accounts:login"), {"username": "sleepy@example.com", "password": PASSWORD})
    assert resp.status_code == 200
    assert "Your account is inactive. Contact the admin." in resp.content.decode()
    assert "_auth_user_id" not in client.session


def test_wrong_password_generic_message(client, student):
    resp = client.post(reverse("accounts:login"), {"username": student.email, "password": "nope"})
    assert resp.status_code == 200 and "_auth_user_id" not in client.session


def test_logout_requires_post(student_client):
    assert student_client.get(reverse("accounts:logout")).status_code == 405
    assert student_client.post(reverse("accounts:logout")).status_code == 302
    assert "_auth_user_id" not in student_client.session


def test_home_routes_by_role(client, student, admin_user):
    client.force_login(student)
    assert client.get(reverse("accounts:home")).url == reverse("students:dashboard")
    client.force_login(admin_user)
    assert client.get(reverse("accounts:home")).url == reverse("adminpanel:dashboard")


def test_student_blocked_from_admin_route(student_client):
    assert student_client.get(reverse("adminpanel:dashboard")).status_code == 403


def test_admin_blocked_from_student_route(admin_client_):
    assert admin_client_.get(reverse("students:dashboard")).status_code == 403


def test_anonymous_redirected_to_login(client):
    resp = client.get(reverse("students:dashboard"))
    assert resp.status_code == 302 and reverse("accounts:login") in resp.url


def test_deactivated_while_logged_in_is_logged_out(student_client, student):
    student.status = "INACTIVE"
    student.save()
    resp = student_client.get(reverse("students:dashboard"))
    assert resp.status_code == 302 and reverse("accounts:login") in resp.url


def test_status_syncs_is_active(student):
    student.status = "INACTIVE"
    student.save()
    student.refresh_from_db()
    assert student.is_active is False
    student.status = "ACTIVE"
    student.save()
    student.refresh_from_db()
    assert student.is_active is True


def test_password_change(student_client, student):
    resp = student_client.post(reverse("accounts:password_change"), {
        "old_password": PASSWORD, "new_password1": "Another-pass-2026!", "new_password2": "Another-pass-2026!"})
    assert resp.status_code == 302
    student.refresh_from_db()
    assert student.check_password("Another-pass-2026!")


def test_create_admin_command_non_interactive():
    call_command("create_admin", email="Boss@Example.com", name="Boss", password=PASSWORD, interactive=False)
    u = get_user_model().objects.get(email="boss@example.com")
    assert u.user_type == "ADMIN" and u.is_staff and u.check_password(PASSWORD)


def test_pages_have_title_suffix_and_disclaimer(client):
    html = client.get(reverse("accounts:login")).content.decode()
    assert "· Eligo</title>" in html
    assert "Independent academic prototype, not affiliated with the official PM Internship Scheme portal." in html
    assert "Eligibility-first, explainable internship matching" in html
