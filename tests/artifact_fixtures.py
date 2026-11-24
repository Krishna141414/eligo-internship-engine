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
    SkillVocab.build(TRAIN_X, BASE_SYNONYMS).to_json(root / "config" / "skills_vocab.json")
    (root / "metrics" / "metrics.json").write_text(json.dumps({"best_model": "RandomForestClassifier"}))
    (root / "data" / "internships_clean.csv").write_text("source_id,internship_title\nS1,Data Science\nS2,Web Development\n")
    if with_sentence_model:
        sm = root / "models" / "sentence_model"
        sm.mkdir()
        (sm / "config.json").write_text('{"fake": true}')
        (sm / "model.safetensors").write_bytes(b"\x00fake-weights")
        (sm / "README.md").write_text("model card")
    return root
