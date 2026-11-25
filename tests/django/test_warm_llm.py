"""warm_llm command and the runserver-only background warm-up (D-025)."""
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from ml_core.llm_extract import WarmResult
from recommendations.apps import should_warm_on_start


def test_warm_llm_command_reports_success():
    out = StringIO()
    with patch("recommendations.management.commands.warm_llm.warm_up",
               return_value=WarmResult(True, 2.6, "qwen3:4b loaded and kept warm for 30m.")):
        call_command("warm_llm", stdout=out)
    assert "qwen3:4b loaded" in out.getvalue()


def test_warm_llm_command_explains_skip_without_failing():
    out = StringIO()
    with patch("recommendations.management.commands.warm_llm.warm_up",
               return_value=WarmResult(False, 0.0, "Ollama isn't running.")):
        call_command("warm_llm", stdout=out)
    assert "Ollama isn't running." in out.getvalue() and "rule-based" in out.getvalue()


def test_should_warm_only_for_runserver_child():
    assert should_warm_on_start(["manage.py", "runserver"], {"RUN_MAIN": "true"}) is True
    assert should_warm_on_start(["manage.py", "runserver", "--noreload"], {}) is True
    assert should_warm_on_start(["manage.py", "runserver"], {}) is False          # autoreload parent
    assert should_warm_on_start(["pytest"], {"RUN_MAIN": "true"}) is False
    assert should_warm_on_start(["manage.py", "migrate"], {}) is False
    assert should_warm_on_start(["manage.py", "runserver"], {"RUN_MAIN": "true", "ELIGO_WARM_LLM": "0"}) is False
