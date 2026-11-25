"""Shared pytest setup and fixtures.

All people, emails and passwords below are TEST FIXTURES (illustrative), not real users.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASSWORD = "Test-pass-2026!"


@pytest.fixture
def make_user(db):
    from django.contrib.auth import get_user_model

    def _make(email="student@example.com", user_type="STUDENT", status="ACTIVE", name="Test Student", **extra):
        User = get_user_model()
        return User.objects.create_user(email=email, password=PASSWORD, name=name, user_type=user_type,
                                        status=status, mobile_number=extra.pop("mobile_number", "9876543210"),
                                        **extra)
    return _make


@pytest.fixture
def student(make_user):
    return make_user()


@pytest.fixture
def other_student(make_user):
    return make_user(email="other@example.com", name="Other Student")


@pytest.fixture
def admin_user(make_user):
    return make_user(email="admin@example.com", user_type="ADMIN", name="Test Admin", is_staff=True)


@pytest.fixture
def student_client(client, student):
    client.force_login(student)
    return client


@pytest.fixture
def admin_client_(client, admin_user):
    client.force_login(admin_user)
    return client
