import os
import sys
import threading

from django.apps import AppConfig


def should_warm_on_start(argv, environ) -> bool:
    """Warm the LLM only in the process that actually serves requests: the runserver child
    (RUN_MAIN=true) or runserver --noreload. Never in tests, migrations or other commands."""
    if environ.get("ELIGO_WARM_LLM", "1") == "0":
        return False
    if len(argv) < 2 or argv[1] != "runserver":
        return False
    return environ.get("RUN_MAIN") == "true" or "--noreload" in argv


class RecommendationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recommendations"

    def ready(self):
        if should_warm_on_start(sys.argv, os.environ):
            threading.Thread(target=_warm_in_background, name="eligo-llm-warmup", daemon=True).start()


def _warm_in_background():
    from ml_core.llm_extract import warm_up
    from recommendations.services import llm_config

    result = warm_up(llm_config())
    print(f"[eligo] LLM warm-up: {result.detail}", flush=True)
