"""Job-role prediction types and inference (spec §3, §12.8; D-008, D-012, D-016, D-021).

The model is trained on canonical skills only. Its scope is 6 computer-science career
fields; predictions for profiles mostly outside that scope are flagged, never shown as confident.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Literal

from ml_core.skills import expand_skill

ScopeStatus = Literal["confident", "low_confidence", "out_of_scope"]
FEATURE_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class ScopeThresholds:
    min_known_skills: int = 2
    min_coverage: float = 0.5
    min_confidence: float = 0.5


def build_feature_schema(binarizer, classes: list[str], scope: ScopeThresholds) -> dict:
    """feature_schema.json: the exact model input (canonical skills vocabulary), the classes, and
    the scope thresholds. Django's profile form and inference both read this file."""
    return {
        "version": FEATURE_SCHEMA_VERSION,
        "input": {"skills": {"type": "list[str]", "vocabulary": [str(s) for s in binarizer.vocabulary_]}},
        "classes": [str(c) for c in classes],
        "scope": asdict(scope),
        "note": "Model input is skills only (canonical names). No academic or assessment features (D-008).",
    }


@dataclass
class JobRolePrediction:
    """`label`/`probability` are None only when no skill was known (the model wasn't called)."""

    label: str | None
    probability: float | None
    probabilities: dict[str, float]
    scope_status: ScopeStatus
    known_skills: list[str]
    unknown_skills: list[str]
    model_name: str
    model_version: str
    top_features: list[tuple[str, float]]


def scope_status(known_skills: int, total_skills: int, confidence: float | None,
                 t: ScopeThresholds) -> ScopeStatus:
    """out_of_scope: too few known skills, or most of the student's skills unknown to the model.
    low_confidence: in scope but the top class probability is below the threshold."""
    if known_skills < t.min_known_skills or total_skills == 0 or known_skills / total_skills < t.min_coverage:
        return "out_of_scope"
    if confidence is None or confidence < t.min_confidence:
        return "low_confidence"
    return "confident"


def _thresholds(schema: dict) -> ScopeThresholds:
    s = schema.get("scope") or {}
    return ScopeThresholds(int(s.get("min_known_skills", 2)), float(s.get("min_coverage", 0.5)),
                           float(s.get("min_confidence", 0.5)))


def split_known(skills: Iterable[str], bundle) -> tuple[list[str], list[str]]:
    """Normalise the student's skills; split into ones the model knows / doesn't know."""
    model_vocab = set(bundle.feature_schema["input"]["skills"]["vocabulary"])
    known, unknown = set(), set()
    for token in skills:
        for s in expand_skill(token, bundle.vocab.synonyms):
            if not s:
                continue
            (known if s in model_vocab else unknown).add(s)
    return sorted(known), sorted(unknown)


def global_feature_importance(pipeline, top_k: int = 10) -> list[tuple[str, float]]:
    names = pipeline[:-1].get_feature_names_out()
    imps = pipeline[-1].feature_importances_
    order = sorted(range(len(names)), key=lambda i: -imps[i])[:top_k]
    return [(str(names[i]), float(imps[i])) for i in order]


def predict_job_role(skills: Iterable[str], bundle, top_k: int = 5) -> JobRolePrediction:
    """Predict a career field from skills only. Never raises for unknown skills: zero known skills
    returns an out_of_scope result without calling the model."""
    known, unknown = split_known(skills, bundle)
    thresholds = _thresholds(bundle.feature_schema)
    common = dict(known_skills=known, unknown_skills=unknown, model_name=bundle.model_name,
                  model_version=bundle.model_version)
    if not known:
        return JobRolePrediction(label=None, probability=None, probabilities={}, scope_status="out_of_scope",
                                 top_features=[], **common)
    model = bundle.best_model
    proba = model.predict_proba([known])[0]
    probabilities = {str(c): float(p) for c, p in zip(model.classes_, proba)}
    label = max(probabilities, key=probabilities.get)
    importance = dict(global_feature_importance(model, top_k=len(model[:-1].get_feature_names_out())))
    own = sorted(((f"skill__{s}", importance.get(f"skill__{s}", 0.0)) for s in known), key=lambda t: -t[1])
    return JobRolePrediction(label=label, probability=probabilities[label], probabilities=probabilities,
                             scope_status=scope_status(len(known), len(known) + len(unknown),
                                                       probabilities[label], thresholds),
                             top_features=own[:top_k], **common)


#: Career field (Student Career dataset label) -> internship title/skill keywords (D-016).
CAREER_FIELD_KEYWORDS: dict[str, list[str]] = {
    "Development": ["web development", "developer", "full stack", "front end", "frontend", "back end", "backend",
                    "app development", "android", "ios", "javascript", "react", "node.js", "php", "wordpress"],
    "Artificial Intelligence": ["artificial intelligence", "machine learning", "deep learning", "ai",
                                "nlp", "natural language processing", "computer vision", "generative ai"],
    "Software Development and Engineering": ["software engineering", "software development", "software developer",
                                             "java", "python", "c++", "software testing", "qa", "devops", "cloud"],
    "Security": ["cyber security", "cybersecurity", "ethical hacking", "network security", "penetration testing",
                 "information security", "security"],
    "Data Science": ["data science", "data analytics", "data analyst", "data analysis", "sql", "power bi",
                     "tableau", "statistics", "business analytics", "python"],
    "User Experience (UX) and User Interface (UI) Design": ["ui/ux design", "ui/ux", "ux", "ui design",
                                                            "user experience", "user interface", "figma",
                                                            "product design", "web design"],
}


def related_internship_keywords(career_field: str) -> list[str]:
    return list(CAREER_FIELD_KEYWORDS.get(career_field, []))
