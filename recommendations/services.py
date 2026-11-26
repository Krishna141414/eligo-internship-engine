"""AI integration services (spec §13).

Artifacts are loaded once per process through ml_core.artifacts.load_bundle (manifest-verified,
never raises) and cached. Nothing here fits or refits a model, vectorizer or encoder (hard rule 4):
the saved TF-IDF vectorizer only transforms, the saved sentence model only encodes.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import numpy as np
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from ml_core.artifacts import ArtifactBundle, ArtifactStatus, load_bundle
from ml_core.explain import explain_ineligible, explain_job_role, explain_recommendation
from ml_core.job_role import predict_job_role as ml_predict_job_role
from ml_core.job_role import related_internship_keywords
from ml_core.llm_extract import analyse_gap, ollama_available
from ml_core.recommender import recommend

_lock = threading.Lock()
_cache: dict[str, tuple[ArtifactBundle | None, ArtifactStatus]] = {}
#: Only the top results get the (slower) optional LLM skill-gap check; the rest use the rule-based one.
LLM_TOP_K = 3


def get_bundle() -> tuple[ArtifactBundle | None, ArtifactStatus]:
    key = str(Path(settings.ELIGO_ARTIFACTS_DIR).resolve())
    with _lock:
        if key not in _cache:
            _cache[key] = load_bundle(Path(settings.ELIGO_ARTIFACTS_DIR))
        return _cache[key]


def reset_bundle_cache() -> None:
    with _lock:
        _cache.clear()


def ai_status() -> ArtifactStatus:
    return get_bundle()[1]


def llm_config():
    """The LLM settings saved by the notebook (artifacts/config/llm_config.json), else the defaults."""
    from ml_core.llm_extract import LLMConfig

    bundle, _ = get_bundle()
    if bundle is not None:
        return bundle.llm
    try:
        return LLMConfig.from_json(Path(settings.ELIGO_ARTIFACTS_DIR) / "config" / "llm_config.json")
    except (OSError, ValueError, TypeError):
        return LLMConfig()


# --- embeddings (D-014) -----------------------------------------------------------------------------
def internship_vectors(internships, bundle: ArtifactBundle) -> np.ndarray:
    """Embedding per internship, in order: the stored embedding if its text hash still matches, else the
    notebook's precomputed row if the text is unchanged, else encode now with the SAVED sentence model
    (inference only) and store the result for next time."""
    from internships.models import Internship

    dim = bundle.internship_vecs.shape[1] if bundle.internship_vecs.ndim == 2 else 384
    out = np.zeros((len(internships), dim), dtype=np.float32)
    to_encode: list[tuple[int, Internship, str]] = []
    for k, i in enumerate(internships):
        h = i.text_hash()
        if i.embedding and i.embedding_text_hash == h:
            out[k] = np.asarray(i.embedding, dtype=np.float32)
        elif i.embedding_row is not None and i.embedding_text_hash == h and i.embedding_row < len(bundle.internship_vecs):
            out[k] = bundle.internship_vecs[i.embedding_row]
        else:
            to_encode.append((k, i, h))
    if to_encode:
        vecs = bundle.sentence_model.encode([i.text_for_matching() for _, i, _ in to_encode], normalize_embeddings=True)
        changed = []
        for (k, i, h), v in zip(to_encode, vecs):
            out[k] = v
            i.embedding = [float(x) for x in v]
            i.embedding_text_hash = h
            changed.append(i)
        Internship.objects.bulk_update(changed, ["embedding", "embedding_text_hash"])
    return out


# --- recommendations ------------------------------------------------------------------------------------
@dataclass
class RecommendationRun:
    run_id: uuid.UUID | None = None
    eligible: list = field(default_factory=list)            # InternshipRecommendation rows
    not_eligible: list = field(default_factory=list)        # [(Internship, [reason, ...])], preview only
    not_eligible_count: int = 0
    reason: str | None = None


def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def generate_recommendations(student) -> RecommendationRun:
    """Gates first, hybrid scores for eligible internships only, explanations, one stored run (D-015)."""
    from assessments.services import latest_qualifying_attempt
    from internships.models import Internship
    from internships.services import internship_facts
    from recommendations.models import InternshipRecommendation
    from students.services import get_profile, student_facts

    profile = get_profile(student)
    missing = profile.missing_fields() if profile else ["qualification", "academic percentage", "skills"]
    if missing:
        return RecommendationRun(reason=f"Complete your profile ({', '.join(missing)}) to get recommendations.")
    bundle, status = get_bundle()
    if bundle is None:
        return RecommendationRun(reason=f"AI engine unavailable. {status.message}")
    attempt = latest_qualifying_attempt(student, profile.qualification)
    if attempt is None:
        return RecommendationRun(reason="Pass an assessment for your qualification with more than 60% "
                                        "to unlock recommendations.")

    score = Decimal(attempt.score_percentage)
    internships = list(Internship.objects.active().order_by("pk"))
    facts = [internship_facts(i) for i in internships]
    sf = student_facts(profile)
    vecs = internship_vectors(internships, bundle)
    student_vec = bundle.sentence_model.encode([sf.text], normalize_embeddings=True)[0]
    result = recommend(sf, facts, score, vectorizer=bundle.vectorizer, internship_vecs=vecs, student_vec=student_vec,
                       weights=bundle.hybrid.weights, today=timezone.localdate(), top_n=bundle.hybrid.top_n)

    by_id = {i.pk: i for i in internships}
    # The LLM never runs here: the page shows the deterministic ranking at once and the top cards
    # fetch their AI second opinion afterwards (D-025).
    llm_ready = bool(getattr(settings, "ELIGO_USE_LLM", True)) and ollama_available(bundle.llm)
    run_id = uuid.uuid4()
    rows = []
    for item in result.eligible:
        internship = by_id[item.internship_id]
        explanation = explain_recommendation(item, result.weights, score)
        gap = analyse_gap(sf.skills, internship.text_for_matching(), vocab=bundle.vocab, config=bundle.llm,
                          use_llm=False)
        explanation["rule_based_gap"] = {"matched": gap.matched, "missing": gap.missing, "detail": gap.detail}
        if item.rank > LLM_TOP_K:
            second = InternshipRecommendation.SecondOpinion.NONE
        elif llm_ready:
            second = InternshipRecommendation.SecondOpinion.PENDING
        else:
            second = InternshipRecommendation.SecondOpinion.UNAVAILABLE
        rows.append(InternshipRecommendation(
            student=student, internship=internship, assessment_attempt=attempt, run_id=run_id,
            qualification_match=True, skill_match_score=item.scores.skill,
            content_similarity_score=item.scores.content, semantic_similarity_score=item.scores.semantic,
            final_match_score=item.scores.final, recommendation_rank=item.rank,
            matched_skills=item.matched, missing_skills=item.missing,
            recommendation_reason=explanation["sentence"], explanation=_json_safe(explanation),
            analysis_method=gap.method, analysis_detail=gap.detail[:300], second_opinion=second))
    InternshipRecommendation.objects.bulk_create(rows)
    saved = list(InternshipRecommendation.objects.filter(run_id=run_id).select_related("internship")
                 .order_by("recommendation_rank"))
    preview = _ineligible_preview(sf, result.not_eligible, by_id)
    return RecommendationRun(run_id=run_id, eligible=saved, not_eligible=preview,
                             not_eligible_count=len(result.not_eligible))


def run_second_opinion(rec):
    """Ask the local LLM to cross-check one pending recommendation (D-024, D-025). Idempotent: only a
    'pending' row is processed, and the update is conditional, so two tabs can't run it twice."""
    from recommendations.models import InternshipRecommendation
    from students.services import get_profile

    Opinion = InternshipRecommendation.SecondOpinion
    if rec.second_opinion != Opinion.PENDING:
        return rec
    bundle, status = get_bundle()
    profile = get_profile(rec.student)
    if bundle is None or profile is None:
        detail = status.message if bundle is None else "Profile missing."
        InternshipRecommendation.objects.filter(pk=rec.pk, second_opinion=Opinion.PENDING).update(
            second_opinion=Opinion.UNAVAILABLE, analysis_detail=detail[:300])
        rec.refresh_from_db()
        return rec
    gap = analyse_gap(profile.skills or [], rec.internship.text_for_matching(), vocab=bundle.vocab,
                      config=bundle.llm, use_llm=True)
    explanation = dict(rec.explanation)
    if gap.method == "llm":
        explanation["llm_gap"] = {"matched": gap.matched, "missing": gap.missing, "detail": gap.detail}
        fields = dict(second_opinion=Opinion.DONE, analysis_method=InternshipRecommendation.Method.LLM)
    else:
        fields = dict(second_opinion=Opinion.UNAVAILABLE)
    InternshipRecommendation.objects.filter(pk=rec.pk, second_opinion=Opinion.PENDING).update(
        explanation=_json_safe(explanation), analysis_detail=gap.detail[:300], **fields)
    rec.refresh_from_db()
    return rec


def _ineligible_preview(student_facts, not_eligible, by_id, limit: int = 10):
    """'Why you can't apply yet': not-eligible internships that share required skills with the student.
    Ordered by the count of shared skills (transparent), never by the hybrid score (rule 3)."""
    skills = set(student_facts.skills)
    groups: dict[tuple, list] = {}     # same title, company and reasons -> shown once (Phase 6.5)
    for iid, res in not_eligible:
        i = by_id[iid]
        shared = len(skills & set(i.required_skills or ()))
        if shared:
            reasons = explain_ineligible(res)
            key = (i.internship_title.casefold(), i.company_name.casefold(), tuple(reasons))
            groups.setdefault(key, []).append((shared, i, reasons))
    scored = []
    for members in groups.values():
        shared, first, reasons = max(members, key=lambda m: m[0])
        first.similar_listings = len(members)
        scored.append((shared, first.internship_title, first, reasons))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [(i, reasons) for _, _, i, reasons in scored[:limit]]


def ineligible_preview_for(student, limit: int = 10):
    """Recompute the not-eligible preview (gates only, no scoring) for the recommendations page."""
    from assessments.services import score_for_gates
    from internships.models import Internship
    from internships.services import internship_facts
    from ml_core.eligibility import evaluate_gates
    from students.services import get_profile, student_facts

    profile = get_profile(student)
    if profile is None or profile.missing_fields():
        return [], 0
    sf = student_facts(profile)
    score, _ = score_for_gates(student, profile.qualification)
    internships = list(Internship.objects.active())
    today = timezone.localdate()
    failing = [(i.pk, res) for i in internships
               if not (res := evaluate_gates(sf, internship_facts(i), score, today)).eligible]
    return _ineligible_preview(sf, failing, {i.pk: i for i in internships}, limit), len(failing)


# --- job role (D-021, D-022) ----------------------------------------------------------------------------------
CAREER_SKILLS_NEEDED = ("Pick at least 3 skills under “Skills the job-role model understands” in your profile "
                        "to get a job-role prediction.")


def predict_job_role(student):
    """Predict from the student's CAREER skills only. Returns (JobRolePrediction | None, message | None)."""
    from assessments.services import latest_qualifying_attempt
    from recommendations.models import JobRolePrediction
    from students.services import get_profile

    profile = get_profile(student)
    if profile is None:
        return None, "Complete your profile first."
    if not profile.career_skills:
        return None, CAREER_SKILLS_NEEDED
    bundle, status = get_bundle()
    if bundle is None:
        return None, f"AI engine unavailable. {status.message}"
    p = ml_predict_job_role(profile.career_skills, bundle)
    pred = JobRolePrediction.objects.create(
        student=student, assessment_attempt=latest_qualifying_attempt(student, profile.qualification),
        predicted_job_role=p.label, probability=p.probability, probabilities=p.probabilities,
        scope_status=p.scope_status, known_skills=p.known_skills, unknown_skills=p.unknown_skills,
        model_name=p.model_name, model_version=p.model_version,
        top_features=[[f, float(v)] for f, v in p.top_features])
    return pred, None


def prediction_explanation(pred) -> dict:
    from ml_core.job_role import JobRolePrediction as MLPrediction

    return explain_job_role(MLPrediction(
        label=pred.predicted_job_role, probability=pred.probability, probabilities=pred.probabilities,
        scope_status=pred.scope_status, known_skills=pred.known_skills, unknown_skills=pred.unknown_skills,
        model_name=pred.model_name, model_version=pred.model_version,
        top_features=[tuple(t) for t in pred.top_features]))


def related_internships(prediction, student, limit: int = 5):
    """Active internships matching the predicted career field's keyword map (D-016) that the student can
    apply to, ordered by semantic similarity to the career field. Returns [(Internship, why)]."""
    from assessments.services import score_for_gates
    from internships.models import Internship
    from internships.services import internship_facts
    from ml_core.eligibility import evaluate_gates
    from students.services import get_profile, student_facts

    if prediction is None or not prediction.predicted_job_role:
        return []
    keywords = related_internship_keywords(prediction.predicted_job_role)
    profile = get_profile(student)
    bundle, _ = get_bundle()
    if not keywords or profile is None or profile.missing_fields() or bundle is None:
        return []
    q = Q()
    for kw in keywords:
        q |= Q(internship_title__icontains=kw) | Q(job_role__icontains=kw) | Q(required_skills__icontains=kw)
    candidates = list(Internship.objects.active().filter(q)[:400])
    sf = student_facts(profile)
    score, _ = score_for_gates(student, profile.qualification)
    today = timezone.localdate()
    eligible = [i for i in candidates if evaluate_gates(sf, internship_facts(i), score, today).eligible]
    if not eligible:
        return []
    field_vec = bundle.sentence_model.encode([f"{prediction.predicted_job_role} internship"], normalize_embeddings=True)[0]
    sims = internship_vectors(eligible, bundle) @ field_vec
    order = np.argsort(-sims)[:limit]
    out = []
    for k in order:
        i = eligible[int(k)]
        text = f"{i.internship_title} {i.job_role} {' '.join(i.required_skills or [])}".lower()
        hit = next((kw for kw in keywords if kw in text), keywords[0])
        out.append((i, f"Matches “{hit}”, one of the {prediction.predicted_job_role} keywords"))
    return out
