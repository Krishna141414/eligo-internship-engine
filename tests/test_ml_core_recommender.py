"""Tests for ml_core.recommender. Texts and profiles here are ILLUSTRATIVE test fixtures."""
from datetime import date
from decimal import Decimal

import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from ml_core.config import REFERENCE_DATE, SKILL_OVERLAP_MIN_DENOMINATOR, HybridWeights
from ml_core.eligibility import InternshipFacts, StudentFacts
from ml_core.recommender import (
    content_similarity,
    hybrid_score,
    recommend,
    semantic_similarity,
    skill_match_score,
)

W = HybridWeights(0.35, 0.40, 0.25)
TEXTS = [
    "python machine learning intern. Skills: python, machine learning, sql",
    "sales telecalling intern. Skills: sales, cold calling",
    "data analyst intern. Skills: excel, sql",
    "graphic design intern. Skills: canva, photoshop",
]


@pytest.fixture
def vec():
    return TfidfVectorizer().fit(TEXTS)


def _unit(i, dim=8):
    v = np.zeros(dim)
    v[i] = 1.0
    return v


def _internship(i, text, skills, **kw):
    base = dict(id=i, status="ACTIVE", deadline=None, required_qualification="Any Graduate",
                specialization=None, minimum_academic_percentage=Decimal("0"),
                required_skills=tuple(skills), text=text)
    base.update(kw)
    return InternshipFacts(**base)


STUDENT = StudentFacts(qualification="B.Tech", specialization="CSE", academic_percentage=Decimal("78"),
                       skills=("python", "sql"), text="Skills: python, sql, machine learning")


# --- component scores --------------------------------------------------------------------------
def test_content_similarity_prefers_relevant(vec):
    s = content_similarity("python machine learning", [TEXTS[0], TEXTS[1]], vec)
    assert s[0] > s[1] and 0.0 <= s.min() and s.max() <= 1.0


def test_content_similarity_does_not_refit(vec):
    before = dict(vec.vocabulary_)
    content_similarity("brand new words xyz", TEXTS, vec)
    assert vec.vocabulary_ == before


def test_semantic_in_range():
    u = _unit(0)
    s = semantic_similarity(u, np.vstack([u, -u, _unit(1)]))
    assert s.tolist() == [1.0, 0.0, 0.0]


def test_semantic_normalises_unnormalised_vectors():
    s = semantic_similarity(np.array([3.0, 4.0]), np.array([[6.0, 8.0]]))
    assert s[0] == pytest.approx(1.0)


def test_skill_match_ratio():
    assert skill_match_score(["python", "sql"], ["python", "excel", "sql", "git"]) == 0.5


def test_skill_overlap_shrinks_short_requirement_lists():
    """D-030: matched / max(required, 3), so 1 of 1 no longer scores a perfect 1.00."""
    assert SKILL_OVERLAP_MIN_DENOMINATOR == 3
    assert skill_match_score(["python"], ["python"]) == pytest.approx(1 / 3)
    assert skill_match_score(["python", "sql"], ["python", "sql"]) == pytest.approx(2 / 3)
    assert skill_match_score(["a", "b", "c"], ["a", "b", "c"]) == 1.0
    assert skill_match_score(["a", "b", "c", "d"], ["a", "b", "c", "d", "e"]) == pytest.approx(0.8)


def test_one_skill_listing_no_longer_outranks_a_broader_match():
    """Same text and embedding: a 1-of-1 listing used to beat a 3-of-4 listing on skill overlap."""
    vec = TfidfVectorizer().fit(["same text"])
    narrow = _internship("narrow", "same text", ["python"])
    broad = _internship("broad", "same text", ["python", "sql", "excel", "git"])
    student = StudentFacts(qualification="B.Tech", specialization="CSE", academic_percentage=Decimal("75"),
                           skills=("python", "sql", "excel"), text="same text")
    r = recommend(student, [narrow, broad], Decimal("75"), vectorizer=vec,
                  internship_vecs=np.vstack([_unit(0), _unit(0)]), student_vec=_unit(0),
                  weights=HybridWeights(0.35, 0.40, 0.25), today=REFERENCE_DATE)
    assert [x.internship_id for x in r.eligible] == ["broad", "narrow"]
    assert r.eligible[0].scores.skill == pytest.approx(0.75) and r.eligible[1].scores.skill == pytest.approx(1 / 3)


def test_skill_match_no_required_skills():
    assert skill_match_score(["python"], []) == 0.0


def test_hybrid_weights_applied():
    b = hybrid_score(1.0, 0.5, 0.0, W)
    assert b.final == pytest.approx(0.55)
    assert b.contributions == pytest.approx({"content": 0.35, "semantic": 0.20, "skill": 0.0})


# --- recommend ---------------------------------------------------------------------------------
def _run(vec, internships, vecs, score=Decimal("75"), top_n=10, student=STUDENT):
    return recommend(student, internships, score, vectorizer=vec, internship_vecs=vecs,
                     student_vec=_unit(0), weights=W, today=REFERENCE_DATE, top_n=top_n)


def test_recommend_excludes_ineligible_even_if_most_similar(vec):
    best_match = _internship(1, TEXTS[0], ["python", "machine learning", "sql"], required_qualification="M.Tech")
    other = _internship(2, TEXTS[2], ["excel", "sql"])
    r = _run(vec, [best_match, other], np.vstack([_unit(0), _unit(1)]))
    assert [x.internship_id for x in r.eligible] == [2]
    assert [iid for iid, _ in r.not_eligible] == [1]
    assert r.not_eligible[0][1].failed[0].gate == "qualification"


def test_recommend_without_qualifying_assessment_ranks_nothing(vec):
    items = [_internship(i, t, []) for i, t in enumerate(TEXTS)]
    r = _run(vec, items, np.vstack([_unit(i) for i in range(4)]), score=Decimal("60.00"))
    assert r.eligible == []
    assert len(r.not_eligible) == 4 and all(not e.eligible for _, e in r.not_eligible)


def test_recommend_orders_by_final_score(vec):
    items = [_internship(1, TEXTS[1], ["sales"]), _internship(2, TEXTS[0], ["python", "sql"])]
    r = _run(vec, items, np.vstack([_unit(5), _unit(0)]))
    assert [x.internship_id for x in r.eligible] == [2, 1]
    top = r.eligible[0]
    assert top.matched == ["python", "sql"] and top.missing == []
    assert top.scores.skill == pytest.approx(2 / 3) and top.scores.semantic == 1.0   # 2 of 2, shrunk (D-030)


def test_rank_tie_break_by_skill():
    # skill weight 0 + identical text and embedding -> equal final scores; the one with more
    # matched skills must rank first (id "a" would win an id-order tie-break)
    vec = TfidfVectorizer().fit(["same text"])
    a = _internship("a", "same text", ["git"])
    b = _internship("b", "same text", ["python"])
    r = recommend(STUDENT, [a, b], Decimal("75"), vectorizer=vec, internship_vecs=np.vstack([_unit(0), _unit(0)]),
                  student_vec=_unit(0), weights=HybridWeights(0.5, 0.5, 0.0), today=REFERENCE_DATE)
    assert r.eligible[0].scores.final == pytest.approx(r.eligible[1].scores.final)
    assert [x.internship_id for x in r.eligible] == ["b", "a"]


def test_top_n_and_ranks_contiguous(vec):
    items = [_internship(i, TEXTS[i % 4], ["python"]) for i in range(7)]
    r = _run(vec, items, np.vstack([_unit(i % 8) for i in range(7)]), top_n=5)
    assert len(r.eligible) == 5
    assert [x.rank for x in r.eligible] == [1, 2, 3, 4, 5]


def test_deadline_gate_uses_given_today(vec):
    closed = _internship(1, TEXTS[0], ["python"], deadline=date(2025, 9, 1))
    r = _run(vec, [closed], np.vstack([_unit(0)]))
    assert r.eligible == [] and r.not_eligible[0][1].failed[0].gate == "status_deadline"
