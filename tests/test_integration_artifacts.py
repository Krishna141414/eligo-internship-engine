"""Integration tests against the REAL artifacts produced by the notebook (skip if absent)."""
import numpy as np
import pandas as pd
import pytest

from ml_core.artifacts import load_bundle
from ml_core.config import ARTIFACTS_DIR
from ml_core.recommender import semantic_similarity
from ml_core.demo import DEMO_PROFILES
from ml_core.job_role import CAREER_SKILL_CROSSWALK, predict_job_role

BUNDLE, STATUS = load_bundle(load_sentence_model=False)
pytestmark = [pytest.mark.slow, pytest.mark.skipif(BUNDLE is None, reason=f"artifacts not available: {STATUS.message}")]


@pytest.fixture(scope="module")
def full_bundle():
    """The bundle WITH the sentence model (heavier; loaded once for this module)."""
    bundle, status = load_bundle()
    if bundle is None:
        pytest.skip(f"sentence model not available: {status.message}")
    return bundle


def test_real_bundle_loads_and_predicts(full_bundle):
    b = full_bundle
    assert b.internship_vecs.shape[0] == len(b.internship_index) > 0
    assert np.allclose(np.linalg.norm(b.internship_vecs, axis=1), 1.0, atol=1e-3)     # stored normalised
    pred = predict_job_role(DEMO_PROFILES["cs"].career_skills, b)
    assert pred.label in b.feature_schema["classes"]
    assert set(pred.probabilities) == set(b.feature_schema["classes"])
    assert sum(pred.probabilities.values()) == pytest.approx(1.0, abs=1e-6)
    assert b.vectorizer.transform(["python machine learning"]).shape[0] == 1         # inference only, no refit


def test_saved_embeddings_match_saved_model_and_data(full_bundle):
    """Re-encoding a sample of internship texts with the saved model reproduces the stored vectors."""
    b = full_bundle
    df = pd.read_csv(ARTIFACTS_DIR / "data" / "internships_clean.csv", usecols=["source_id", "text"],
                     dtype=str, keep_default_na=False)
    by_id = dict(zip(df["source_id"], df["text"]))
    sample = [b.internship_index[i] for i in (0, 1, len(b.internship_index) // 2, len(b.internship_index) - 1)]
    fresh = b.sentence_model.encode([by_id[e["source_id"]] for e in sample], normalize_embeddings=True)
    stored = b.internship_vecs[[e["row"] for e in sample]]
    assert np.min(np.sum(fresh * stored, axis=1)) > 0.999


def test_semantic_ordering_real_model(full_bundle):
    encode = full_bundle.sentence_model.encode
    student = encode(["Skills: python, machine learning, deep learning. Interested in AI."], normalize_embeddings=True)[0]
    relevant, unrelated = encode(["Machine Learning intern. Skills: python, machine learning, tensorflow",
                                  "Retail sales associate. Skills: cold calling, negotiation, store billing"],
                                 normalize_embeddings=True)
    scores = semantic_similarity(student, np.vstack([relevant, unrelated]))
    assert 0.0 <= scores.min() and scores.max() <= 1.0
    assert scores[0] > scores[1] + 0.1


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
