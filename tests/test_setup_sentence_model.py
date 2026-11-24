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
