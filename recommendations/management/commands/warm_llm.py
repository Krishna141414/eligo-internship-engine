"""Preload the local LLM so the first AI second opinion isn't slow (D-025).

    python manage.py warm_llm

Safe to run any time: if Ollama or the model isn't there it says so, and Eligo keeps using the
rule-based skill check.
"""
from django.core.management.base import BaseCommand

from ml_core.llm_extract import warm_up
from recommendations.services import llm_config


class Command(BaseCommand):
    help = "Load the configured Ollama model into memory and keep it warm."

    def add_arguments(self, parser):
        parser.add_argument("--keep-alive", default="30m")

    def handle(self, *args, keep_alive="30m", **options):
        config = llm_config()
        self.stdout.write(f"Warming {config.model} at {config.base_url} ...")
        result = warm_up(config, keep_alive=keep_alive)
        if result.ok:
            self.stdout.write(self.style.SUCCESS(result.detail))
        else:
            self.stdout.write(self.style.WARNING(result.detail))
            self.stdout.write("Eligo still works: the rule-based skill check is used instead.")
