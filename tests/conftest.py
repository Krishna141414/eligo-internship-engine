"""Shared pytest setup.

Django settings are wired in once the Django project exists (PLAN Task 11).
Until then, ml_core tests run as plain pytest tests.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
