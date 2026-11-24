"""Tests for ml_core.job_role. The bundle/pipeline fixtures are ILLUSTRATIVE (tests/artifact_fixtures.py)."""
from ml_core.job_role import ScopeThresholds, build_feature_schema
from ml_core.skills import SkillBinarizer


def test_build_feature_schema_lists_vocabulary_classes_and_scope():
    b = SkillBinarizer(min_count=1).fit([["python", "sql"], ["html"]])
    schema = build_feature_schema(b, ["Data Science", "Development"], ScopeThresholds(3, 0.6, 0.55))
    assert schema["input"]["skills"]["vocabulary"] == ["html", "python", "sql"]
    assert schema["classes"] == ["Data Science", "Development"]
    assert schema["scope"] == {"min_known_skills": 3, "min_coverage": 0.6, "min_confidence": 0.55}
    assert "skills only" in schema["note"]
