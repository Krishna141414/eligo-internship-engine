"""Tests for ml_core.llm_extract. Ollama's HTTP API is the external boundary that gets mocked;
normalisation, validation, retry and fallback are exercised for real."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from ml_core.llm_extract import (
    SKILL_SCHEMA,
    LLMConfig,
    analyse_gap,
    extract_skills,
    ollama_available,
)
from ml_core.skills import BASE_SYNONYMS, SkillVocab, extract_skills_rule_based

TEXT = "Looking for an intern who knows Python, SQL and machine learning."
CFG = LLMConfig()


@pytest.fixture
def vocab():
    return SkillVocab.build([["python", "sql", "machine learning", "excel"]], BASE_SYNONYMS)


def _response(content: str) -> MagicMock:
    """Mirror of Ollama's non-streaming /api/chat response."""
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = {"model": CFG.model, "created_at": "2026-11-24T10:00:00Z",
                           "message": {"role": "assistant", "content": content},
                           "done": True, "done_reason": "stop"}
    return r


def test_falls_back_when_ollama_down(vocab):
    with patch("ml_core.llm_extract.requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
        r = extract_skills(TEXT, vocab=vocab, config=CFG)
    assert r.method == "rule_based"
    assert r.skills == extract_skills_rule_based(TEXT, vocab) == ["machine learning", "python", "sql"]
    assert "not reachable" in r.detail.lower()


def test_llm_path_normalises_output(vocab):
    with patch("ml_core.llm_extract.requests.post", return_value=_response('{"skills": ["Py", "ML"]}')):
        r = extract_skills(TEXT, vocab=vocab, config=CFG)
    assert r.method == "llm" and r.skills == ["machine learning", "python"]


def test_invalid_json_retries_once_then_falls_back(vocab):
    with patch("ml_core.llm_extract.requests.post", return_value=_response("not json")) as post:
        r = extract_skills(TEXT, vocab=vocab, config=CFG)
    assert post.call_count == 2
    assert r.method == "rule_based" and "invalid" in r.detail.lower()


def test_schema_violation_counts_as_invalid(vocab):
    with patch("ml_core.llm_extract.requests.post", return_value=_response('{"tools": ["python"]}')) as post:
        r = extract_skills(TEXT, vocab=vocab, config=CFG)
    assert post.call_count == 2 and r.method == "rule_based"


def test_second_attempt_can_succeed(vocab):
    responses = [_response("oops"), _response('{"skills": ["SQL"]}')]
    with patch("ml_core.llm_extract.requests.post", side_effect=responses):
        r = extract_skills(TEXT, vocab=vocab, config=CFG)
    assert r.method == "llm" and r.skills == ["sql"]


def test_request_body(vocab):
    with patch("ml_core.llm_extract.requests.post", return_value=_response('{"skills": []}')) as post:
        extract_skills(TEXT, vocab=vocab, config=CFG)
    url = post.call_args.args[0]
    body = post.call_args.kwargs["json"]
    assert url == "http://localhost:11434/api/chat"
    assert body["model"] == "qwen3:4b"
    assert body["format"] == SKILL_SCHEMA
    assert body["stream"] is False and body["think"] is False
    assert body["options"]["temperature"] == 0
    assert post.call_args.kwargs["timeout"] == CFG.timeout_s
    assert TEXT in body["messages"][-1]["content"]


def test_llm_skill_phrases_mapped_to_vocab(vocab):
    # real qwen3:4b output for a posting: task phrases rather than bare skill names
    content = '{"skills": ["clean data in Python", "write SQL queries", "build simple machine learning models"]}'
    with patch("ml_core.llm_extract.requests.post", return_value=_response(content)):
        r = extract_skills(TEXT, vocab=vocab, config=CFG)
    assert r.method == "llm" and r.skills == ["machine learning", "python", "sql"]


def test_llm_skills_outside_vocab_dropped(vocab):
    with patch("ml_core.llm_extract.requests.post",
               return_value=_response('{"skills": ["Underwater basket weaving"]}')):
        r = extract_skills(TEXT, vocab=vocab, config=CFG)
    assert r.skills == [] and r.method == "llm"


def test_use_llm_false_never_calls_http(vocab):
    with patch("ml_core.llm_extract.requests.post") as post:
        r = extract_skills(TEXT, vocab=vocab, config=CFG, use_llm=False)
    post.assert_not_called()
    assert r.method == "rule_based"


def test_gap_uses_normalised_sets(vocab):
    g = analyse_gap(["Py"], "Need Python and SQL", vocab=vocab, config=CFG, use_llm=False)
    assert g.matched == ["python"] and g.missing == ["sql"] and g.method == "rule_based"


def test_ollama_available_false_on_error():
    with patch("ml_core.llm_extract.requests.get", side_effect=requests.exceptions.ConnectionError()):
        assert ollama_available(CFG) is False


def _tags(*names):
    """Mirror of Ollama's GET /api/tags response."""
    r = MagicMock(status_code=200)
    r.json.return_value = {"models": [{"name": n, "model": n, "size": 1} for n in names]}
    return r


def test_ollama_available_true_when_model_installed():
    with patch("ml_core.llm_extract.requests.get", return_value=_tags("qwen3:4b", "llama3.2:3b")) as get:
        assert ollama_available(CFG) is True
    assert get.call_args.args[0] == "http://localhost:11434/api/tags"


def test_ollama_available_false_when_model_missing():
    # server up but the configured model isn't pulled yet -> treat the LLM as unavailable (no slow failing calls)
    with patch("ml_core.llm_extract.requests.get", return_value=_tags("llama3.2:3b")):
        assert ollama_available(CFG) is False


def test_config_json_roundtrip(tmp_path):
    p = tmp_path / "llm_config.json"
    CFG.to_json(p)
    assert LLMConfig.from_json(p) == CFG
