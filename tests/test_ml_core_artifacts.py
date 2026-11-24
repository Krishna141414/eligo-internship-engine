"""Tests for ml_core.artifacts: SHA-256 manifest, verification, never-raising loader."""
import json
import shutil

import pytest

from ml_core.artifacts import load_bundle, verify_manifest, verify_sentence_model, write_manifest
from ml_core.config import DEFAULT_WEIGHTS
from tests.artifact_fixtures import build_fake_artifacts


@pytest.fixture
def fake_artifacts(tmp_path):
    root = build_fake_artifacts(tmp_path / "artifacts")
    write_manifest(root, best_model_name="RandomForestClassifier", model_version="1",
                   sentence_model_revision="abc123")
    return root


def test_manifest_roundtrip_ok(fake_artifacts):
    status = verify_manifest(fake_artifacts)
    assert status.ok and status.missing == [] and status.mismatched == []


def test_manifest_records_versions_and_model(fake_artifacts):
    m = json.loads((fake_artifacts / "manifest.json").read_text())
    assert m["best_model"] == {"name": "RandomForestClassifier", "version": "1"}
    assert m["sentence_model"]["revision"] == "abc123"
    assert {"python", "scikit-learn", "sentence-transformers", "torch"} <= set(m["versions"])
    assert "vectorizers/tfidf.joblib" in m["files"] and len(m["files"]["vectorizers/tfidf.joblib"]["sha256"]) == 64


def test_tampered_file_detected(fake_artifacts):
    with open(fake_artifacts / "vectorizers" / "tfidf.joblib", "ab") as f:
        f.write(b"x")
    status = verify_manifest(fake_artifacts)
    assert not status.ok and status.mismatched == ["vectorizers/tfidf.joblib"]


def test_missing_manifest_returns_status_not_exception(tmp_path):
    bundle, status = load_bundle(tmp_path)
    assert bundle is None and not status.ok and "notebook" in status.message.lower()


def test_missing_file_listed(fake_artifacts):
    (fake_artifacts / "metrics" / "metrics.json").unlink()
    status = verify_manifest(fake_artifacts)
    assert not status.ok and "metrics/metrics.json" in status.missing


def test_required_file_absent_from_manifest_is_missing(fake_artifacts):
    m = json.loads((fake_artifacts / "manifest.json").read_text())
    del m["files"]["config/feature_schema.json"]
    (fake_artifacts / "manifest.json").write_text(json.dumps(m))
    assert "config/feature_schema.json" in verify_manifest(fake_artifacts).missing


def test_path_outside_artifacts_rejected(fake_artifacts):
    m = json.loads((fake_artifacts / "manifest.json").read_text())
    m["files"]["../evil.joblib"] = {"sha256": "0" * 64, "bytes": 1}
    (fake_artifacts / "manifest.json").write_text(json.dumps(m))
    status = verify_manifest(fake_artifacts)
    assert not status.ok and "../evil.joblib" in status.mismatched


def test_load_bundle_ok_without_sentence_model(fake_artifacts):
    bundle, status = load_bundle(fake_artifacts, load_sentence_model=False)
    assert status.ok, status.message
    assert bundle.hybrid.weights == DEFAULT_WEIGHTS
    assert bundle.model_name == "RandomForestClassifier" and bundle.model_version == "1"
    assert bundle.internship_vecs.shape == (2, 384) and len(bundle.internship_index) == 2
    assert "python" in bundle.vocab.canonical
    assert bundle.sentence_model is None


def test_load_bundle_tampered_returns_none(fake_artifacts):
    with open(fake_artifacts / "models" / "best_model.joblib", "ab") as f:
        f.write(b"x")
    bundle, status = load_bundle(fake_artifacts, load_sentence_model=False)
    assert bundle is None and not status.ok


def test_missing_sentence_model_message_names_setup_script(fake_artifacts):
    shutil.rmtree(fake_artifacts / "models" / "sentence_model")
    status = verify_sentence_model(fake_artifacts)
    assert not status.ok and "setup_sentence_model.py" in status.message
    # the rest of the artifacts are still fine
    assert verify_manifest(fake_artifacts).ok


def test_sentence_model_readme_not_hashed(fake_artifacts):
    (fake_artifacts / "models" / "sentence_model" / "README.md").write_text("edited card")
    assert verify_sentence_model(fake_artifacts).ok


def test_sentence_model_weights_tamper_detected(fake_artifacts):
    (fake_artifacts / "models" / "sentence_model" / "model.safetensors").write_bytes(b"other")
    status = verify_sentence_model(fake_artifacts)
    assert not status.ok and "models/sentence_model/model.safetensors" in status.mismatched
