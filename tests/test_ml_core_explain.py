"""Tests for ml_core.explain: explanations contain only computed values. Fixtures are illustrative."""
from decimal import Decimal

import pytest

from ml_core.config import HybridWeights
from ml_core.eligibility import EligibilityResult, GateResult
from ml_core.explain import explain_ineligible, explain_job_role, explain_recommendation
from ml_core.job_role import JobRolePrediction
from ml_core.recommender import RankedInternship, hybrid_score

W = HybridWeights(0.35, 0.40, 0.25)
PASSED = EligibilityResult([GateResult("qualification", True, "ok"), GateResult("assessment", True, "ok")])


@pytest.fixture
def item():
    # content 0.2, semantic 0.8, skill 0.75 -> semantic contributes most (0.32)
    return RankedInternship(internship_id=7, rank=2, scores=hybrid_score(0.2, 0.8, 0.75, W),
                            matched=["python", "sql", "excel"], missing=["git"], gates=PASSED,
                            required_skills=["excel", "git", "python", "sql"])


@pytest.fixture
def item_no_skills():
    return RankedInternship(internship_id=8, rank=5, scores=hybrid_score(0.4, 0.5, 0.0, W),
                            matched=[], missing=[], gates=PASSED, required_skills=[])


def test_explanation_values_equal_computed(item):
    e = explain_recommendation(item, W, Decimal("72.5"))
    assert sum(c["contribution"] for c in e["components"]) == pytest.approx(item.scores.final)
    assert e["final_score"] == pytest.approx(item.scores.final)
    by_name = {c["name"]: c for c in e["components"]}
    assert by_name["semantic"]["score"] == pytest.approx(0.8) and by_name["semantic"]["weight"] == 0.40
    assert by_name["semantic"]["contribution"] == pytest.approx(0.32)


def test_sentence_mentions_rank_and_real_skill_counts(item):
    s = explain_recommendation(item, W, Decimal("72.5"))["sentence"]
    assert "#2" in s and "3 of 4" in s


def test_short_skill_list_shrinkage_is_explained():
    """D-030: 1 of 1 matched scores 0.33, and the sentence says why (numbers from the computation)."""
    one = RankedInternship(internship_id=9, rank=1, scores=hybrid_score(0.5, 0.5, 1 / 3, W),
                           matched=["python"], missing=[], gates=PASSED, required_skills=["python"])
    s = explain_recommendation(one, W, Decimal("72.5"))["sentence"]
    assert "1 of 1" in s and "counted out of 3" in s and "0.33" in s


def test_no_shrinkage_note_for_three_or_more_skills(item):
    assert "counted out of" not in explain_recommendation(item, W, Decimal("72.5"))["sentence"]


def test_largest_contributor_named(item):
    s = explain_recommendation(item, W, Decimal("72.5"))["sentence"]
    assert "semantic" in s.lower() and "0.32" in s


def test_explanation_for_internship_without_skills(item_no_skills):
    s = explain_recommendation(item_no_skills, W, Decimal("72.5"))["sentence"]
    assert "lists no required skills" in s and "0 of 0" not in s


def test_no_invented_skills(item):
    e = explain_recommendation(item, W, Decimal("72.5"))
    assert e["matched_skills"] == item.matched and e["missing_skills"] == item.missing


def test_assessment_block_uses_strict_threshold(item):
    a = explain_recommendation(item, W, Decimal("72.5"))["assessment"]
    assert a == {"score": "72.50%", "threshold": "60%", "passed": True}


def test_gates_copied_from_result(item):
    e = explain_recommendation(item, W, Decimal("72.5"))
    assert e["gates"] == [{"gate": "qualification", "passed": True, "reason": "ok"},
                          {"gate": "assessment", "passed": True, "reason": "ok"}]


def test_explain_ineligible_lists_only_failed_reasons():
    r = EligibilityResult([GateResult("qualification", False, "Requires B.Tech."),
                           GateResult("assessment", True, "ok"),
                           GateResult("academic_percentage", False, "Requires 60%.")])
    assert explain_ineligible(r) == ["Requires B.Tech.", "Requires 60%."]


# --- job role ------------------------------------------------------------------------------------
def _pred(status, label="Data Science", p=0.82, known=("python", "sql"), unknown=()):
    return JobRolePrediction(label=label, probability=p, probabilities={label: p} if label else {},
                             scope_status=status, known_skills=list(known), unknown_skills=list(unknown),
                             model_name="RandomForestClassifier", model_version="1",
                             top_features=[("skill__python", 0.12)])


@pytest.fixture
def pred_confident():
    return _pred("confident")


@pytest.fixture
def pred_low():
    return _pred("low_confidence", p=0.35)


def test_explain_job_role_has_skills_only_note(pred_confident):
    e = explain_job_role(pred_confident)
    assert "skills only" in e["note"]
    assert e["confidence_pct"] == 82 and e["scope_message"] == ""


def test_explain_job_role_low_confidence_has_scope_message(pred_low):
    e = explain_job_role(pred_low)
    assert e["scope_status"] == "low_confidence"
    assert "6 computer-science career fields" in e["scope_message"] and "35%" in e["scope_message"]


def test_explain_job_role_out_of_scope_counts_known_skills():
    e = explain_job_role(_pred("out_of_scope", p=0.6, known=("python",), unknown=("sales", "cooking")))
    assert "1 of your 3 skills" in e["scope_message"]


def test_explain_job_role_no_known_skills_no_prediction():
    e = explain_job_role(_pred("out_of_scope", label=None, p=None, known=(), unknown=("cooking",)))
    assert e["confidence_pct"] is None and "no prediction" in e["scope_message"].lower()
