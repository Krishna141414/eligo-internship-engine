"""AI integration services (PLAN Task 16). Artifacts are loaded once per process through
ml_core.artifacts.load_bundle (manifest-verified, never raises) and cached."""
from __future__ import annotations

import threading
from pathlib import Path

from django.conf import settings

from ml_core.artifacts import ArtifactBundle, ArtifactStatus, load_bundle

_lock = threading.Lock()
_cache: dict[str, tuple[ArtifactBundle | None, ArtifactStatus]] = {}


def get_bundle() -> tuple[ArtifactBundle | None, ArtifactStatus]:
    key = str(Path(settings.ELIGO_ARTIFACTS_DIR).resolve())
    with _lock:
        if key not in _cache:
            _cache[key] = load_bundle(Path(settings.ELIGO_ARTIFACTS_DIR))
        return _cache[key]


def reset_bundle_cache() -> None:
    with _lock:
        _cache.clear()


def ai_status() -> ArtifactStatus:
    return get_bundle()[1]
