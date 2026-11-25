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


@pytest.fixture
def fake_artifacts(tmp_path, settings):
    """A manifest-verified FAKE artifacts dir (test fixture) wired into settings; bundle cache reset."""
    from ml_core.artifacts import write_manifest
    from recommendations.services import reset_bundle_cache
    from tests.artifact_fixtures import build_fake_artifacts, fixture_internship_row, write_internship_rows

    root = build_fake_artifacts(tmp_path / "artifacts")
    write_internship_rows(root, [
        fixture_internship_row("T1", "Data Science", skills=("python", "sql")),
        fixture_internship_row("T2", "Web Development", skills=("html", "css"), location="Work from home"),
        fixture_internship_row("T3", "MBA Strategy Intern", skills=("excel",), qualification="MBA", location="Mumbai"),
    ])
    write_manifest(root, best_model_name="RandomForestClassifier", model_version="1", sentence_model_revision="x")
    settings.ELIGO_ARTIFACTS_DIR = root
    reset_bundle_cache()
    yield root
    reset_bundle_cache()
