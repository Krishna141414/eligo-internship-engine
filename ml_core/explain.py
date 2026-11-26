"""Explainable-AI output built ONLY from computed values (spec §6).

Every number in an explanation comes from the recommender's ScoreBreakdown, the gate results,
or the model's prediction. Sentences are templates filled with those values; nothing is invented.
"""
from __future__ import annotations

from decimal import Decimal

from ml_core.config import PASS_THRESHOLD, SKILL_OVERLAP_MIN_DENOMINATOR, HybridWeights
from ml_core.eligibility import EligibilityResult, fmt_pct, is_qualified
from ml_core.job_role import JobRolePrediction
from ml_core.recommender import RankedInternship

COMPONENT_LABELS: dict[str, str] = {
    "content": "content (TF-IDF) similarity",
    "semantic": "semantic (sentence-transformer) similarity",
    "skill": "skill overlap",
}

SKILLS_ONLY_NOTE = ("This model was trained on skills only. Your assessment score controls internship "
                    "eligibility but is not a model input, because the public training data has no "
                    "comparable score.")
SCOPE = "6 computer-science career fields"


def _skill_list(skills: list[str], limit: int = 3) -> str:
    shown = ", ".join(skills[:limit])
    return shown + (f" and {len(skills) - limit} more" if len(skills) > limit else "")


def explain_recommendation(item: RankedInternship, weights: HybridWeights,
                           assessment_score: Decimal | None) -> dict:
    s = item.scores
    components = [
        {"name": name, "label": COMPONENT_LABELS[name], "score": score,
         "weight": getattr(weights, name), "contribution": s.contributions[name]}
        for name, score in (("content", s.content), ("semantic", s.semantic), ("skill", s.skill))
    ]
    top = max(components, key=lambda c: c["contribution"])
    n_required = len(item.matched) + len(item.missing)

    parts = [f"Ranked #{item.rank} with a {s.final * 100:.0f}% match."]
    if n_required:
        matched_txt = f" ({_skill_list(item.matched)})" if item.matched else ""
        parts.append(f"You match {len(item.matched)} of {n_required} required skills{matched_txt}.")
        if n_required < SKILL_OVERLAP_MIN_DENOMINATOR:
            parts.append(f"This listing names only {n_required} skill{'s' if n_required != 1 else ''}, so the skill "
                         f"overlap is counted out of {SKILL_OVERLAP_MIN_DENOMINATOR} ({s.skill:.2f}).")
    else:
        parts.append("This internship lists no required skills, so the skill score is 0.")
    parts.append(f"The largest part of the score came from {top['label']} (+{top['contribution']:.2f}).")

    return {
        "gates": [{"gate": g.gate, "passed": g.passed, "reason": g.reason} for g in item.gates.gates],
        "assessment": {
            "score": fmt_pct(assessment_score) if assessment_score is not None else None,
            "threshold": f"{PASS_THRESHOLD}%",
            "passed": assessment_score is not None and is_qualified(assessment_score),
        },
        "matched_skills": list(item.matched),
        "missing_skills": list(item.missing),
        "components": components,
        "final_score": s.final,
        "rank": item.rank,
        "sentence": " ".join(parts),
    }


def explain_ineligible(result: EligibilityResult) -> list[str]:
    return [g.reason for g in result.failed]


def explain_job_role(prediction: JobRolePrediction) -> dict:
    p = prediction
    pct = round(p.probability * 100) if p.probability is not None else None
    total = len(p.known_skills) + len(p.unknown_skills)
    if p.scope_status == "out_of_scope":
        if p.label is None:
            message = (f"Your skills are outside what this model covers ({SCOPE}). It doesn't recognise any "
                       f"of them, so no prediction was made. Add skills from the list to try again.")
        else:
            message = (f"Your profile is mostly outside what this model covers ({SCOPE}). It recognises "
                       f"{len(p.known_skills)} of your {total} skills, so the result is only a tentative "
                       f"closest match.")
    elif p.scope_status == "low_confidence":
        message = (f"Low confidence: the model is only {pct}% sure. It covers {SCOPE}, so treat the "
                   f"closest match as tentative.")
    else:
        message = ""
    return {
        "label": p.label,
        "confidence_pct": pct,
        "scope_status": p.scope_status,
        "scope_message": message,
        "note": SKILLS_ONLY_NOTE,
        "known_skills": list(p.known_skills),
        "unknown_skills": list(p.unknown_skills),
        "top_features": [{"feature": f.removeprefix("skill__"), "importance": v} for f, v in p.top_features],
        "model": f"{p.model_name} v{p.model_version}",
    }
