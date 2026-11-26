"""Test utility: builds a small but structurally complete FAKE artifacts directory.

Everything here is an illustrative test fixture (tiny pipelines fitted on hand-written rows,
a fake sentence-model folder), never real training output.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from ml_core.config import DEFAULT_WEIGHTS
from ml_core.llm_extract import LLMConfig
from ml_core.skills import BASE_SYNONYMS, SkillBinarizer, SkillVocab

TRAIN_X = [["python", "machine learning"], ["python", "deep learning"], ["machine learning", "statistics"],
           ["html", "css"], ["javascript", "html"], ["css", "javascript"],
           ["network security", "linux"], ["cryptography", "linux"], ["network security", "cryptography"],
           ["python", "statistics"], ["html", "javascript"], ["linux", "cryptography"]]
TRAIN_Y = ["Data Science", "Data Science", "Data Science", "Development", "Development", "Development",
           "Security", "Security", "Security", "Data Science", "Development", "Security"]
INTERNSHIP_TEXTS = ["Data Science. Skills: python, machine learning", "Web Development. Skills: html, css"]


def fitted_pipeline(model: str = "rf") -> Pipeline:
    clf = (RandomForestClassifier(n_estimators=25, random_state=0) if model == "rf"
           else DecisionTreeClassifier(random_state=0))
    return Pipeline([("skills", SkillBinarizer(min_count=1)), ("clf", clf)]).fit(TRAIN_X, TRAIN_Y)


def build_fake_artifacts(root: Path, *, with_sentence_model: bool = True) -> Path:
    from ml_core.job_role import ScopeThresholds, build_feature_schema  # Task 9

    root.mkdir(parents=True, exist_ok=True)
    for sub in ("models", "vectorizers", "embeddings", "config", "metrics", "data", "figures"):
        (root / sub).mkdir(exist_ok=True)
    rf, dt = fitted_pipeline("rf"), fitted_pipeline("dt")
    joblib.dump(rf, root / "models" / "rf.joblib")
    joblib.dump(dt, root / "models" / "dt.joblib")
    joblib.dump(rf, root / "models" / "best_model.joblib")
    joblib.dump(rf.named_steps["skills"], root / "models" / "preprocess.joblib")
    joblib.dump(TfidfVectorizer().fit(INTERNSHIP_TEXTS), root / "vectorizers" / "tfidf.joblib")
    np.save(root / "embeddings" / "internships.npy", np.eye(2, 384, dtype=np.float32))
    (root / "embeddings" / "internship_index.json").write_text(json.dumps(
        [{"source_id": "S1", "row": 0, "text_hash": "h1"}, {"source_id": "S2", "row": 1, "text_hash": "h2"}]))
    (root / "config" / "hybrid_config.json").write_text(json.dumps({
        "weights": {"content": DEFAULT_WEIGHTS.content, "semantic": DEFAULT_WEIGHTS.semantic,
                    "skill": DEFAULT_WEIGHTS.skill}, "top_n": 10, "version": "1"}))
    schema = build_feature_schema(rf.named_steps["skills"], list(rf.classes_), ScopeThresholds())
    (root / "config" / "feature_schema.json").write_text(json.dumps(schema))
    LLMConfig().to_json(root / "config" / "llm_config.json")
    SkillVocab.build(TRAIN_X + [["sql", "excel", "canva"]], BASE_SYNONYMS).to_json(root / "config" / "skills_vocab.json")
    (root / "metrics" / "metrics.json").write_text(json.dumps({"best_model": "RandomForestClassifier"}))
    (root / "data" / "internships_clean.csv").write_text("source_id,internship_title\nS1,Data Science\nS2,Web Development\n")
    if with_sentence_model:
        sm = root / "models" / "sentence_model"
        sm.mkdir()
        (sm / "config.json").write_text('{"fake": true}')
        (sm / "model.safetensors").write_bytes(b"\x00fake-weights")
        (sm / "README.md").write_text("model card")
    return root


CLEAN_COLUMNS = ["source_id", "company_name", "internship_title", "job_role", "description", "description_derived",
                 "required_qualification", "specialization", "minimum_academic_percentage", "required_skills",
                 "required_skills_text", "location", "work_mode", "stipend_text", "stipend_min", "stipend_max",
                 "duration_text", "duration_months", "application_deadline", "eligibility_criteria",
                 "start_date", "derived_fields", "text"]


def fixture_internship_row(source_id, title="Data Science", company="Acme Analytics (fixture)",
                           skills=("python", "sql"), location="Bangalore", qualification="Any Graduate",
                           specialization="", deadline="2025-10-15", stipend="₹ 10,000 - 15,000 /month"):
    """One row in the exact internships_clean.csv format written by the notebook (test fixture)."""
    from ml_core.preprocessing import build_internship_text
    description = f"{title} internship at {company}. Required skills: {', '.join(skills)}."
    return {"source_id": source_id, "company_name": company, "internship_title": title, "job_role": title,
            "description": description, "description_derived": True, "required_qualification": qualification,
            "specialization": specialization, "minimum_academic_percentage": 0,
            "required_skills": json.dumps(list(skills)), "required_skills_text": ", ".join(skills),
            "location": location, "work_mode": "Remote" if location == "Work from home" else "On-site",
            "stipend_text": stipend, "stipend_min": 10000.0, "stipend_max": 15000.0, "duration_text": "3 Months",
            "duration_months": 3.0, "application_deadline": deadline, "eligibility_criteria": "", "start_date": "Immediately",
            "derived_fields": json.dumps(["description", "minimum_academic_percentage", "required_qualification"]),
            "text": build_internship_text(title, title, list(skills), "", "", description)}


def write_internship_rows(root: Path, rows: list[dict]) -> None:
    """Replace the fake artifacts' internships_clean.csv + internship_index.json + embeddings with `rows`."""
    import csv
    import hashlib
    with open(root / "data" / "internships_clean.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CLEAN_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    index = [{"source_id": r["source_id"], "row": i, "text_hash": hashlib.sha256(r["text"].encode()).hexdigest()}
             for i, r in enumerate(rows)]
    (root / "embeddings" / "internship_index.json").write_text(json.dumps(index))
    vecs = np.zeros((len(rows), 384), dtype=np.float32)
    for i in range(len(rows)):
        vecs[i, i % 384] = 1.0
    np.save(root / "embeddings" / "internships.npy", vecs)


class FakeEncoder:
    """Deterministic stand-in for the sentence model (test fixture): bag-of-words hashed into 384 dims,
    L2-normalised. Records every batch it encodes so tests can check caching."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def encode(self, texts, normalize_embeddings=True, **kwargs):
        import hashlib
        texts = list(texts)
        self.calls.append(texts)
        out = np.zeros((len(texts), 384), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in str(t).lower().replace(",", " ").replace(".", " ").split():
                out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 384] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1, norms)
