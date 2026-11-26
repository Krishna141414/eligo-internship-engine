"""Tests for scripts/setup_sentence_model.py. The download is the external boundary and is faked;
manifest verification runs for real against a fake artifacts directory."""
import shutil

import pytest

from ml_core.artifacts import write_manifest
from scripts.setup_sentence_model import main
from tests.artifact_fixtures import build_fake_artifacts


@pytest.fixture
def artifacts(tmp_path):
    root = build_fake_artifacts(tmp_path / "artifacts")
    write_manifest(root, best_model_name="RandomForestClassifier", model_version="1", sentence_model_revision="x")
    shutil.rmtree(root / "models" / "sentence_model")   # as after a fresh clone (git-ignored)
    return root


def _good_download(target, name, revision):
    target.mkdir(parents=True, exist_ok=True)
    (target / "config.json").write_text('{"fake": true}')
    (target / "model.safetensors").write_bytes(b"\x00fake-weights")


def _tampered_download(target, name, revision):
    _good_download(target, name, revision)
    (target / "model.safetensors").write_bytes(b"different")


def test_script_succeeds_when_download_matches_manifest(artifacts, capsys):
    assert main(["--artifacts-dir", str(artifacts)], download=_good_download) == 0
    assert "verified" in capsys.readouterr().out.lower()


def test_script_verifies_against_manifest(artifacts, capsys):
    assert main(["--artifacts-dir", str(artifacts)], download=_tampered_download) == 1
    out = capsys.readouterr().out
    assert "models/sentence_model/model.safetensors" in out


def test_script_passes_pinned_revision(artifacts):
    seen = {}

    def spy(target, name, revision):
        seen.update(name=name, revision=revision)
        _good_download(target, name, revision)

    main(["--artifacts-dir", str(artifacts)], download=spy)
    assert seen == {"name": "sentence-transformers/all-MiniLM-L6-v2",
                    "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"}


def test_script_without_manifest_explains(tmp_path, capsys):
    assert main(["--artifacts-dir", str(tmp_path)], download=_good_download) == 1
    assert "notebook" in capsys.readouterr().out.lower()


def test_packages_that_shape_the_saved_model_are_pinned_exactly():
    """Fresh-clone test (Phase 7): transformers 5.24.1 was published after the model was saved with
    5.24.0, and the version string it writes into config.json broke the SHA-256 check. Everything that
    writes into the saved model's files must be pinned to the installed version."""
    import re
    from importlib.metadata import version
    from pathlib import Path

    req = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text(encoding="utf-8")
    pins = dict(re.findall(r"^([A-Za-z0-9_.-]+)==([^\s#]+)", req, flags=re.M))
    pins = {k.lower(): v for k, v in pins.items()}
    for pkg in ("sentence-transformers", "transformers", "tokenizers", "huggingface-hub", "safetensors", "torch"):
        assert pkg in pins, f"{pkg} is not pinned in requirements.txt"
        assert version(pkg).split("+")[0] == pins[pkg].split("+")[0], (pkg, version(pkg), pins[pkg])
