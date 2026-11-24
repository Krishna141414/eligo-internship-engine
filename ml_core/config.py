"""Project-wide paths, constants and small config objects for ml_core."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR: Path = ROOT_DIR / "artifacts"
DATA_DIR: Path = ROOT_DIR / "data"

#: Assessment eligibility: a score must be strictly greater than this (exactly 60 fails).
PASS_THRESHOLD: Decimal = Decimal("60")

#: Imported postings were scraped 21-28 Sep 2025; their deadlines are judged against
#: the last scrape day instead of "today" (docs/DECISIONS.md D-007).
REFERENCE_DATE: date = date(2025, 9, 28)

SENTENCE_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
#: Hugging Face commit hash, pinned on first download (PLAN Task 10, D-020).
SENTENCE_MODEL_REVISION: str = ""
SENTENCE_MODEL_DIR: Path = ARTIFACTS_DIR / "models" / "sentence_model"

RANDOM_STATE: int = 42


@dataclass(frozen=True)
class HybridWeights:
    """Weights of the three hybrid score components. Non-negative, sum to 1."""

    content: float
    semantic: float
    skill: float

    def __post_init__(self) -> None:
        values = (self.content, self.semantic, self.skill)
        if any(v < 0 for v in values):
            raise ValueError("Hybrid weights must be non-negative.")
        if not math.isclose(sum(values), 1.0, abs_tol=1e-6):
            raise ValueError(f"Hybrid weights must sum to 1 (got {sum(values):.4f}).")


@dataclass(frozen=True)
class HybridConfig:
    weights: HybridWeights
    top_n: int
    version: str


DEFAULT_WEIGHTS = HybridWeights(content=0.35, semantic=0.40, skill=0.25)


def load_hybrid_config(path: Path) -> HybridConfig:
    """Read hybrid_config.json written by the notebook; validates the weights."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    w = data["weights"]
    return HybridConfig(
        weights=HybridWeights(float(w["content"]), float(w["semantic"]), float(w["skill"])),
        top_n=int(data["top_n"]),
        version=str(data["version"]),
    )
