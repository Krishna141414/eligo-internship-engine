"""LIVE test against a local Ollama (PENDING – Ollama until the model is pulled).

Skips automatically when Ollama isn't running or the configured model isn't installed, so the
suite never depends on Ollama. The text below is an ILLUSTRATIVE fixture.
"""
import pytest
import requests

from ml_core.llm_extract import LLMConfig, extract_skills
from ml_core.skills import BASE_SYNONYMS, SkillVocab

CFG = LLMConfig()


def _model_installed() -> bool:
    try:
        tags = requests.get(f"{CFG.base_url}/api/tags", timeout=2).json()
    except (requests.RequestException, ValueError):
        return False
    return any(m.get("name", "").startswith(CFG.model) for m in tags.get("models", []))


pytestmark = [pytest.mark.slow,
              pytest.mark.skipif(not _model_installed(), reason=f"Ollama with {CFG.model} not available")]


def test_live_llm_extracts_skills_from_text():
    vocab = SkillVocab.build([["python", "sql", "machine learning", "excel", "communication"]], BASE_SYNONYMS)
    text = ("Data science intern wanted. You will clean data in Python, write SQL queries and "
            "build simple machine learning models. Good communication is a plus.")
    r = extract_skills(text, vocab=vocab, config=CFG)
    assert r.method == "llm", r.detail
    assert {"python", "sql"} <= set(r.skills)
