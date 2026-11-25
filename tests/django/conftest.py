"""Django tests never touch the real artifacts: by default ELIGO_ARTIFACTS_DIR points at an empty
folder (AI engine unavailable). Tests opt in with the `fake_artifacts` or `ai_bundle` fixtures."""
import pytest


@pytest.fixture(autouse=True)
def _fast_password_hashing(settings):
    # Tests only: production keeps Django's default PBKDF2 hasher (hard rule: secure password storage).
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def _no_real_artifacts(tmp_path_factory, settings):
    from recommendations.services import reset_bundle_cache

    settings.ELIGO_ARTIFACTS_DIR = tmp_path_factory.mktemp("no_artifacts")
    reset_bundle_cache()
    yield
    reset_bundle_cache()


@pytest.fixture
def ai_bundle(fake_artifacts, monkeypatch):
    """The FAKE artifacts loaded as an AI bundle with a fake encoder, served by get_bundle()."""
    from django.core.management import call_command

    from ml_core.artifacts import ArtifactStatus, load_bundle
    from recommendations import services
    from tests.artifact_fixtures import FakeEncoder

    bundle, status = load_bundle(fake_artifacts, load_sentence_model=False)
    assert status.ok, status.message
    bundle.sentence_model = FakeEncoder()
    monkeypatch.setattr(services, "get_bundle", lambda: (bundle, ArtifactStatus(True, "AI engine ready.")))
    monkeypatch.setattr(services, "ollama_available", lambda cfg, timeout_s=2.0: False)
    call_command("load_internships")
    return bundle
