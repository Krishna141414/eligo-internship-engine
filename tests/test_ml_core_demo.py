"""DEMO profiles are illustrative and must be labelled DEMO everywhere (hard rule 7)."""
from decimal import Decimal

from ml_core.demo import DEMO_PROFILES


def test_demo_profiles_labelled():
    assert DEMO_PROFILES and all(p.label.startswith("DEMO") for p in DEMO_PROFILES.values())


def test_demo_profiles_cover_pass_and_fail_cases():
    scores = [p.assessment_score for p in DEMO_PROFILES.values()]
    assert any(s > Decimal("60") for s in scores) and any(s <= Decimal("60") for s in scores)


def test_demo_profiles_have_career_skills_and_expected_career():
    cs = DEMO_PROFILES["cs"]
    assert cs.career_skills and cs.expected_career
