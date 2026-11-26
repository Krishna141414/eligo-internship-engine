"""Hybrid internship recommender (spec §4).

Order of operations is the whole point: eligibility gates first, then scoring for the
eligible internships only. Similarity can never pull an ineligible internship into the list.

final = w_content · content + w_semantic · semantic + w_skill · skill
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Protocol, Sequence

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ml_core.config import SKILL_OVERLAP_MIN_DENOMINATOR, HybridWeights
from ml_core.eligibility import EligibilityResult, InternshipFacts, StudentFacts, evaluate_gates
from ml_core.skills import compare_skills


class Encoder(Protocol):
    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> np.ndarray: ...


def content_similarity(student_text: str, internship_texts: Sequence[str], vectorizer) -> np.ndarray:
    """TF-IDF cosine similarity. Uses the saved vectorizer's `transform` only (never refits)."""
    if len(internship_texts) == 0:
        return np.zeros(0)
    student = vectorizer.transform([student_text])
    docs = vectorizer.transform(list(internship_texts))
    return np.clip(cosine_similarity(student, docs)[0], 0.0, 1.0)


def semantic_similarity(student_vec: np.ndarray, internship_vecs: np.ndarray) -> np.ndarray:
    """Cosine similarity of sentence embeddings, clipped to [0, 1]."""
    vecs = np.atleast_2d(np.asarray(internship_vecs, dtype=float))
    if vecs.shape[0] == 0:
        return np.zeros(0)
    s = np.asarray(student_vec, dtype=float).ravel()
    s_norm = np.linalg.norm(s)
    v_norm = np.linalg.norm(vecs, axis=1)
    denom = np.where(v_norm * s_norm == 0, 1.0, v_norm * s_norm)
    return np.clip(vecs @ s / denom, 0.0, 1.0)


def skill_match_score(student_skills: Iterable[str], required_skills: Iterable[str]) -> float:
    """|matched| / max(|required|, SKILL_OVERLAP_MIN_DENOMINATOR) (D-030); 0.0 when none are listed.

    The floor on the denominator shrinks short skill lists: matching the only listed skill gives
    1/3, not a perfect 1.00, so a one-skill listing can't outrank a broader, better match."""
    required = set(required_skills)
    if not required:
        return 0.0
    return len(required & set(student_skills)) / max(len(required), SKILL_OVERLAP_MIN_DENOMINATOR)


@dataclass
class ScoreBreakdown:
    content: float
    semantic: float
    skill: float
    contributions: dict[str, float]
    final: float


def hybrid_score(content: float, semantic: float, skill: float, weights: HybridWeights) -> ScoreBreakdown:
    contributions = {
        "content": weights.content * float(content),
        "semantic": weights.semantic * float(semantic),
        "skill": weights.skill * float(skill),
    }
    return ScoreBreakdown(float(content), float(semantic), float(skill), contributions,
                          sum(contributions.values()))


@dataclass
class RankedInternship:
    internship_id: Any
    rank: int
    scores: ScoreBreakdown
    matched: list[str]
    missing: list[str]
    gates: EligibilityResult
    required_skills: list[str] = field(default_factory=list)


@dataclass
class RecommendationResult:
    eligible: list[RankedInternship]
    not_eligible: list[tuple[Any, EligibilityResult]]
    weights: HybridWeights
    assessment_score: Decimal | None


def recommend(student: StudentFacts, internships: Sequence[InternshipFacts],
              assessment_score: Decimal | None, *, vectorizer, internship_vecs: np.ndarray,
              student_vec: np.ndarray, weights: HybridWeights, today: date,
              top_n: int = 10) -> RecommendationResult:
    """Gate every internship, score only the eligible ones, rank, return both lists.

    `internship_vecs[i]` is the embedding of `internships[i]`.
    Ranking: final score desc, then skill score desc, then id (stable, deterministic).
    """
    eligible_idx: list[int] = []
    gate_results: list[EligibilityResult] = []
    not_eligible: list[tuple[Any, EligibilityResult]] = []
    for i, internship in enumerate(internships):
        result = evaluate_gates(student, internship, assessment_score, today)
        gate_results.append(result)
        if result.eligible:
            eligible_idx.append(i)
        else:
            not_eligible.append((internship.id, result))

    ranked: list[RankedInternship] = []
    if eligible_idx:
        chosen = [internships[i] for i in eligible_idx]
        content = content_similarity(student.text, [it.text for it in chosen], vectorizer)
        semantic = semantic_similarity(student_vec, np.asarray(internship_vecs)[eligible_idx])
        scored = []
        for k, it in enumerate(chosen):
            skill = skill_match_score(student.skills, it.required_skills)
            breakdown = hybrid_score(content[k], semantic[k], skill, weights)
            cmp = compare_skills(student.skills, it.required_skills)
            scored.append((it, breakdown, cmp, gate_results[eligible_idx[k]]))
        scored.sort(key=lambda t: (-t[1].final, -t[1].skill, str(t[0].id)))
        for rank, (it, breakdown, cmp, gates) in enumerate(scored[:top_n], start=1):
            ranked.append(RankedInternship(it.id, rank, breakdown, cmp.matched, cmp.missing, gates,
                                           sorted(it.required_skills)))
    return RecommendationResult(ranked, not_eligible, weights, assessment_score)
