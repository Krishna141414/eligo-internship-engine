"""Integration tests against the REAL artifacts produced by the notebook (skip if absent)."""
import pytest

from ml_core.artifacts import load_bundle
from ml_core.demo import DEMO_PROFILES
from ml_core.job_role import CAREER_SKILL_CROSSWALK, predict_job_role

BUNDLE, STATUS = load_bundle(load_sentence_model=False)
pytestmark = [pytest.mark.slow, pytest.mark.skipif(BUNDLE is None, reason=f"artifacts not available: {STATUS.message}")]


def test_crosswalk_targets_exist_in_schema_vocab():
    vocab = set(BUNDLE.feature_schema["input"]["skills"]["vocabulary"])
    missing = {k: [t for t in v if t not in vocab] for k, v in CAREER_SKILL_CROSSWALK.items()}
    assert not {k: v for k, v in missing.items() if v}


def test_demo_cs_profile_confident_and_correct():
    p = DEMO_PROFILES["cs"]
    pred = predict_job_role(p.career_skills, BUNDLE)
    assert pred.scope_status == "confident", (pred.label, pred.probability, pred.unknown_skills)
    assert pred.label == p.expected_career


def test_demo_career_skills_all_known_to_model():
    vocab = set(BUNDLE.feature_schema["input"]["skills"]["vocabulary"])
    for p in DEMO_PROFILES.values():
        assert set(p.career_skills) <= vocab, p.label
