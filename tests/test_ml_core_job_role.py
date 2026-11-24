"""Tests for ml_core.job_role. The bundle/pipeline fixtures are ILLUSTRATIVE (tests/artifact_fixtures.py)."""
import pytest

from ml_core.artifacts import load_bundle, write_manifest
from ml_core.job_role import (
    CAREER_FIELD_KEYWORDS,
    ScopeThresholds,
    build_feature_schema,
    global_feature_importance,
    predict_job_role,
    related_internship_keywords,
    scope_status,
    split_known,
)
from ml_core.skills import SkillBinarizer
from tests.artifact_fixtures import build_fake_artifacts

REAL_CLASSES = {"Development", "Artificial Intelligence", "Software Development and Engineering", "Security",
                "Data Science", "User Experience (UX) and User Interface (UI) Design"}


@pytest.fixture
def bundle(tmp_path):
    root = build_fake_artifacts(tmp_path / "artifacts")
    write_manifest(root, best_model_name="RandomForestClassifier", model_version="1", sentence_model_revision="x")
    b, status = load_bundle(root, load_sentence_model=False)
    assert status.ok, status.message
    return b


def test_build_feature_schema_lists_vocabulary_classes_and_scope():
    b = SkillBinarizer(min_count=1).fit([["python", "sql"], ["html"]])
    schema = build_feature_schema(b, ["Data Science", "Development"], ScopeThresholds(3, 0.6, 0.55))
    assert schema["input"]["skills"]["vocabulary"] == ["html", "python", "sql"]
    assert schema["classes"] == ["Data Science", "Development"]
    assert schema["scope"] == {"min_known_skills": 3, "min_coverage": 0.6, "min_confidence": 0.55}
    assert "skills only" in schema["note"]


@pytest.mark.parametrize("known,total,conf,exp", [
    (0, 3, None, "out_of_scope"),
    (1, 1, 0.9, "out_of_scope"),       # too few known skills
    (2, 5, 0.9, "out_of_scope"),       # coverage 40% < 50%
    (3, 4, 0.4, "low_confidence"),
    (3, 4, 0.5, "confident"),          # boundary: >= min_confidence
    (2, 4, 0.9, "confident"),          # boundary: coverage exactly 50%, known exactly 2
])
def test_scope_status_rules(known, total, conf, exp):
    assert scope_status(known, total, conf, ScopeThresholds(2, 0.5, 0.5)) == exp


def test_split_known_normalises_and_separates(bundle):
    known, unknown = split_known(["Python", "ML", "Cooking"], bundle)
    assert known == ["machine learning", "python"] and unknown == ["cooking"]


def test_scope_status_no_known_skills_no_model_call(bundle):
    p = predict_job_role(["basket weaving"], bundle)
    assert p.scope_status == "out_of_scope" and p.label is None and p.probability is None
    assert p.unknown_skills == ["basket weaving"] and p.probabilities == {}


def test_scope_status_mostly_unknown_is_out_of_scope(bundle):
    p = predict_job_role(["python", "sales", "telecalling", "cooking"], bundle)
    assert p.scope_status == "out_of_scope" and p.label is not None


def test_scope_status_thresholds_read_from_schema(bundle):
    bundle.feature_schema["scope"]["min_confidence"] = 1.01
    assert predict_job_role(["python", "machine learning"], bundle).scope_status == "low_confidence"


def test_confident_prediction_for_clear_profile(bundle):
    p = predict_job_role(["python", "machine learning", "statistics"], bundle)
    assert p.label == "Data Science" and p.scope_status == "confident" and p.probability >= 0.5


def test_prediction_label_in_schema_classes(bundle):
    p = predict_job_role(["python", "machine learning"], bundle)
    assert p.label in bundle.feature_schema["classes"] and 0 <= p.probability <= 1


def test_probabilities_sum_to_one(bundle):
    p = predict_job_role(["html", "css"], bundle)
    assert sum(p.probabilities.values()) == pytest.approx(1.0)
    assert p.probability == max(p.probabilities.values())


def test_known_skills_are_only_schema_skills(bundle):
    p = predict_job_role(["python", "html", "sales"], bundle)
    assert set(p.known_skills) <= set(bundle.feature_schema["input"]["skills"]["vocabulary"])


def test_top_features_are_students_own_skills(bundle):
    p = predict_job_role(["python", "machine learning"], bundle)
    assert {f.removeprefix("skill__") for f, _ in p.top_features} <= {"python", "machine learning"}
    assert p.model_name == "RandomForestClassifier" and p.model_version == "1"


def test_global_feature_importance_sorted(bundle):
    imps = global_feature_importance(bundle.best_model, top_k=5)
    assert len(imps) == 5 and all(name.startswith("skill__") for name, _ in imps)
    assert [v for _, v in imps] == sorted((v for _, v in imps), reverse=True)


def test_keyword_map_covers_all_classes():
    assert set(CAREER_FIELD_KEYWORDS) == REAL_CLASSES
    assert "machine learning" in related_internship_keywords("Artificial Intelligence")
    assert related_internship_keywords("Astronaut") == []
