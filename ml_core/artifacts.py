"""Artifact manifest (SHA-256) and the trusted loader used by Django (hard rules 13 and 14).

`load_bundle()` never raises. On any problem (missing manifest, missing or tampered file,
load error) it returns (None, ArtifactStatus(ok=False, message=...)), and the web app shows a
friendly banner instead of a 500. Pickled models are only loaded from inside the artifacts
directory and only after their hash matches the manifest written by the notebook.
"""
from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from ml_core.config import ARTIFACTS_DIR, SENTENCE_MODEL_NAME, HybridConfig, load_hybrid_config
from ml_core.llm_extract import LLMConfig
from ml_core.skills import SkillVocab

MANIFEST = "manifest.json"
SENTENCE_MODEL_SUBDIR = "models/sentence_model"
SETUP_HINT = "Run `.\\.venv\\Scripts\\python.exe scripts\\setup_sentence_model.py` (or re-run the notebook)."
NOTEBOOK_HINT = "Ask the admin to run the notebook (notebooks/eligo_engine.ipynb) to create the AI artifacts."

REQUIRED_FILES: tuple[str, ...] = (
    "models/best_model.joblib",
    "models/dt.joblib",
    "models/rf.joblib",
    "models/preprocess.joblib",
    "vectorizers/tfidf.joblib",
    "embeddings/internships.npy",
    "embeddings/internship_index.json",
    "config/hybrid_config.json",
    "config/feature_schema.json",
    "config/llm_config.json",
    "config/skills_vocab.json",
    "metrics/metrics.json",
    "data/internships_clean.csv",
)
_VERSIONED_PACKAGES = ("scikit-learn", "sentence-transformers", "torch", "numpy", "pandas", "joblib")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_model_card(rel: str) -> bool:
    return rel.startswith(SENTENCE_MODEL_SUBDIR + "/") and rel.endswith("README.md")


def write_manifest(artifacts_dir: Path, *, best_model_name: str, model_version: str,
                   sentence_model_revision: str, extra: dict | None = None) -> Path:
    artifacts_dir = Path(artifacts_dir)
    files: dict[str, dict[str, Any]] = {}
    for p in sorted(artifacts_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(artifacts_dir).as_posix()
        if rel == MANIFEST or _is_model_card(rel):
            continue
        files[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    versions = {"python": platform.python_version()}
    for pkg in _VERSIONED_PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = None
    manifest = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "best_model": {"name": best_model_name, "version": model_version},
        "sentence_model": {"name": SENTENCE_MODEL_NAME, "revision": sentence_model_revision,
                           "dir": SENTENCE_MODEL_SUBDIR},
        "versions": versions,
        "files": files,
    } | (extra or {})
    out = artifacts_dir / MANIFEST
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out


@dataclass
class ArtifactStatus:
    ok: bool
    message: str
    missing: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)


def _read_manifest(artifacts_dir: Path) -> dict | None:
    try:
        return json.loads((Path(artifacts_dir) / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _safe_path(artifacts_dir: Path, rel: str) -> Path | None:
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts or ":" in rel:
        return None
    path = (Path(artifacts_dir) / pure).resolve()
    root = Path(artifacts_dir).resolve()
    return path if path == root or root in path.parents else None


def _check(artifacts_dir: Path, entries: dict[str, dict]) -> tuple[list[str], list[str]]:
    missing, mismatched = [], []
    for rel, info in sorted(entries.items()):
        path = _safe_path(artifacts_dir, rel)
        if path is None:
            mismatched.append(rel)
        elif not path.is_file():
            missing.append(rel)
        elif sha256_file(path) != info.get("sha256"):
            mismatched.append(rel)
    return missing, mismatched


def verify_manifest(artifacts_dir: Path) -> ArtifactStatus:
    """Every non-sentence-model artifact listed in the manifest exists and matches its SHA-256,
    and every REQUIRED_FILES entry is listed."""
    manifest = _read_manifest(artifacts_dir)
    if manifest is None:
        return ArtifactStatus(False, f"AI artifacts not found (no {MANIFEST}). {NOTEBOOK_HINT}")
    entries = {k: v for k, v in manifest.get("files", {}).items()
               if not k.startswith(SENTENCE_MODEL_SUBDIR + "/")}
    missing, mismatched = _check(artifacts_dir, entries)
    missing += [r for r in REQUIRED_FILES if r not in entries and r not in missing]
    if missing or mismatched:
        return ArtifactStatus(False, f"AI artifacts are incomplete or changed since the notebook created them. "
                                     f"{NOTEBOOK_HINT}", sorted(missing), sorted(mismatched))
    return ArtifactStatus(True, "AI artifacts verified.")


def verify_sentence_model(artifacts_dir: Path) -> ArtifactStatus:
    manifest = _read_manifest(artifacts_dir)
    if manifest is None:
        return ArtifactStatus(False, f"AI artifacts not found (no {MANIFEST}). {NOTEBOOK_HINT}")
    entries = {k: v for k, v in manifest.get("files", {}).items() if k.startswith(SENTENCE_MODEL_SUBDIR + "/")}
    if not entries or not (Path(artifacts_dir) / SENTENCE_MODEL_SUBDIR).is_dir():
        return ArtifactStatus(False, f"The sentence model isn't set up yet. {SETUP_HINT}",
                              missing=sorted(entries) or [SENTENCE_MODEL_SUBDIR])
    missing, mismatched = _check(artifacts_dir, entries)
    if missing or mismatched:
        return ArtifactStatus(False, f"The sentence model files don't match the manifest. {SETUP_HINT}",
                              missing, mismatched)
    return ArtifactStatus(True, "Sentence model verified.")


@dataclass
class ArtifactBundle:
    best_model: Any
    model_name: str
    model_version: str
    feature_schema: dict
    vectorizer: Any
    sentence_model: Any | None
    internship_vecs: np.ndarray
    internship_index: list[dict]
    hybrid: HybridConfig
    llm: LLMConfig
    vocab: SkillVocab
    metrics: dict
    manifest: dict


def load_bundle(artifacts_dir: Path | None = None, *, load_sentence_model: bool = True
                ) -> tuple[ArtifactBundle | None, ArtifactStatus]:
    """Verify, then load every artifact Django needs. Never raises."""
    root = Path(artifacts_dir) if artifacts_dir is not None else ARTIFACTS_DIR
    try:
        status = verify_manifest(root)
        if not status.ok:
            return None, status
        sentence_model = None
        if load_sentence_model:
            sm_status = verify_sentence_model(root)
            if not sm_status.ok:
                return None, sm_status
            from sentence_transformers import SentenceTransformer  # heavy import, only when needed
            sentence_model = SentenceTransformer(str(root / SENTENCE_MODEL_SUBDIR), device="cpu",
                                                 local_files_only=True)
        import joblib

        manifest = _read_manifest(root) or {}
        read_json = lambda rel: json.loads((root / rel).read_text(encoding="utf-8"))  # noqa: E731
        bundle = ArtifactBundle(
            best_model=joblib.load(root / "models/best_model.joblib"),
            model_name=manifest["best_model"]["name"],
            model_version=str(manifest["best_model"]["version"]),
            feature_schema=read_json("config/feature_schema.json"),
            vectorizer=joblib.load(root / "vectorizers/tfidf.joblib"),
            sentence_model=sentence_model,
            internship_vecs=np.load(root / "embeddings/internships.npy", allow_pickle=False),
            internship_index=read_json("embeddings/internship_index.json"),
            hybrid=load_hybrid_config(root / "config/hybrid_config.json"),
            llm=LLMConfig.from_json(root / "config/llm_config.json"),
            vocab=SkillVocab.from_json(root / "config/skills_vocab.json"),
            metrics=read_json("metrics/metrics.json"),
            manifest=manifest,
        )
        return bundle, ArtifactStatus(True, "AI engine ready.")
    except Exception as exc:  # noqa: BLE001 - the contract is "never raise"; the message says what broke
        return None, ArtifactStatus(False, f"AI artifacts could not be loaded ({type(exc).__name__}: {exc}). "
                                           f"{NOTEBOOK_HINT}")
