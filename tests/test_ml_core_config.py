"""Tests for ml_core.config: hybrid weight validation and config loading."""
import json
import math
from dataclasses import astuple

import pytest

from ml_core.config import DEFAULT_WEIGHTS, HybridWeights, load_hybrid_config


def test_default_weights_sum_to_one():
    assert math.isclose(sum(astuple(DEFAULT_WEIGHTS)), 1.0)


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1"):
        HybridWeights(0.5, 0.5, 0.5)


def test_negative_weight_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        HybridWeights(-0.1, 0.6, 0.5)


def test_load_hybrid_config_roundtrip(tmp_path):
    path = tmp_path / "hybrid_config.json"
    path.write_text(json.dumps({
        "weights": {"content": 0.3, "semantic": 0.5, "skill": 0.2},
        "top_n": 10,
        "version": "1",
    }), encoding="utf-8")
    cfg = load_hybrid_config(path)
    assert cfg.weights == HybridWeights(0.3, 0.5, 0.2)
    assert cfg.top_n == 10
    assert cfg.version == "1"


def test_load_hybrid_config_rejects_bad_weights(tmp_path):
    path = tmp_path / "hybrid_config.json"
    path.write_text(json.dumps({"weights": {"content": 0.9, "semantic": 0.9, "skill": 0.0},
                                "top_n": 10, "version": "1"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_hybrid_config(path)
