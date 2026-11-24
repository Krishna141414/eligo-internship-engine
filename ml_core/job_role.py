"""Job-role prediction types and inference (spec §3, §12.8; D-008, D-012, D-016, D-021).

The model is trained on canonical skills only. Its scope is 6 computer-science career
fields; predictions for profiles mostly outside that scope are flagged, never shown as confident.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ScopeStatus = Literal["confident", "low_confidence", "out_of_scope"]


@dataclass(frozen=True)
class ScopeThresholds:
    min_known_skills: int = 2
    min_coverage: float = 0.5
    min_confidence: float = 0.5


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
