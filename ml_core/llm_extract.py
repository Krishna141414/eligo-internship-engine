"""Optional local-LLM skill analysis via Ollama, with a deterministic rule-based fallback (spec §5).

The LLM is never required. If Ollama isn't running, times out, or returns invalid output twice,
the rule-based path (synonym map + vocabulary phrase matching) runs instead. Every result says
which method produced it (`method: "llm" | "rule_based"`), and the UI shows that.
No RAG, no vector database: one prompt, one JSON-schema-constrained answer.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Iterable, Literal

import requests
from pydantic import BaseModel, Field, StringConstraints, ValidationError

from ml_core.skills import SkillVocab, compare_skills, extract_skills_rule_based, normalise_skills

Method = Literal["llm", "rule_based"]


@dataclass(frozen=True)
class LLMConfig:
    base_url: str = "http://localhost:11434"
    model: str = "qwen3:4b"
    alternative_model: str = "qwen2.5:3b"
    timeout_s: float = 20.0
    temperature: float = 0.0
    prompt_version: str = "1"
    num_predict: int = 256

    def to_json(self, path: Path) -> None:
        data = asdict(self) | {"schema": SKILL_SCHEMA, "system_prompt": SYSTEM_PROMPT}
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> "LLMConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


class SkillList(BaseModel):
    skills: list[Annotated[str, StringConstraints(min_length=1, max_length=60)]] = Field(max_length=40)


SKILL_SCHEMA: dict = SkillList.model_json_schema()
SYSTEM_PROMPT = ("You extract skills from text. Return only JSON matching the schema: "
                 '{"skills": [...]}. List concrete technical and professional skills, tools and '
                 "languages that the text explicitly mentions. Do not add skills that are not in the text.")


@dataclass
class ExtractionResult:
    skills: list[str]
    method: Method
    detail: str


@dataclass
class GapResult:
    matched: list[str]
    missing: list[str]
    method: Method
    detail: str


def ollama_available(config: LLMConfig, timeout_s: float = 2.0) -> bool:
    """True only if the Ollama server answers AND the configured model is installed, so a missing model
    never causes slow failing calls; the rule-based path runs instead."""
    try:
        resp = requests.get(f"{config.base_url}/api/tags", timeout=timeout_s)
        if resp.status_code != 200:
            return False
        names = [m.get("name", "") for m in resp.json().get("models", [])]
    except (requests.RequestException, ValueError, AttributeError):
        return False
    return any(n == config.model or n.startswith(config.model + "-") or n == f"{config.model}:latest" for n in names)


def _ask_llm(text: str, config: LLMConfig) -> SkillList:
    body = {
        "model": config.model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": f"Text:\n{text}"}],
        "stream": False,
        "think": False,
        "format": SKILL_SCHEMA,
        "options": {"temperature": config.temperature, "num_predict": config.num_predict},
    }
    response = requests.post(f"{config.base_url}/api/chat", json=body, timeout=config.timeout_s)
    response.raise_for_status()
    return SkillList.model_validate_json(response.json()["message"]["content"])


def llm_items_to_vocab(items: Iterable[str], vocab: SkillVocab) -> list[str]:
    """Map LLM output to canonical skills. Small models often return phrases ("clean data in Python")
    instead of bare names, so each item is matched exactly first, then searched with the
    deterministic phrase matcher. Anything outside the vocabulary is dropped."""
    out: set[str] = set()
    for item in items:
        direct = normalise_skills([item], vocab)
        out.update(direct if direct else extract_skills_rule_based(item, vocab))
    return sorted(out)


def extract_skills(text: str, *, vocab: SkillVocab, config: LLMConfig, use_llm: bool = True) -> ExtractionResult:
    """LLM extraction (one retry on invalid output) -> normalised to the vocabulary; else rule-based."""
    def fallback(reason: str) -> ExtractionResult:
        return ExtractionResult(extract_skills_rule_based(text, vocab), "rule_based", reason)

    if not use_llm:
        return fallback("Rule-based extraction (LLM not used).")
    for _attempt in range(2):
        try:
            parsed = _ask_llm(text, config)
        except requests.RequestException as exc:
            return fallback(f"Ollama not reachable ({type(exc).__name__}); used rule-based extraction.")
        except (ValidationError, ValueError, KeyError, TypeError):
            continue
        return ExtractionResult(llm_items_to_vocab(parsed.skills, vocab), "llm",
                                f"Extracted by {config.model} (prompt v{config.prompt_version}).")
    return fallback("LLM returned invalid JSON twice; used rule-based extraction.")


def analyse_gap(student_skills: Iterable[str], internship_text: str, *, vocab: SkillVocab,
                config: LLMConfig, use_llm: bool = True) -> GapResult:
    """Required skills from the internship text (LLM or rule-based) vs the student's normalised skills."""
    required = extract_skills(internship_text, vocab=vocab, config=config, use_llm=use_llm)
    cmp = compare_skills(normalise_skills(list(student_skills), vocab), required.skills)
    return GapResult(cmp.matched, cmp.missing, required.method, required.detail)
