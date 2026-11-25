"""Internship helpers shared by views, the loader and the recommendation service."""
from __future__ import annotations

import difflib
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from internships.models import Internship
from ml_core.config import REFERENCE_DATE
from ml_core.eligibility import QUALIFICATION_HIERARCHY, InternshipFacts
from ml_core.skills import SkillVocab, expand_skill, split_skills


def skill_vocab() -> SkillVocab | None:
    """The canonical skill vocabulary: from the loaded AI bundle, else read-only from skills_vocab.json."""
    from recommendations.services import get_bundle

    bundle, _ = get_bundle()
    if bundle is not None:
        return bundle.vocab
    path = Path(settings.ELIGO_ARTIFACTS_DIR) / "config" / "skills_vocab.json"
    try:
        return SkillVocab.from_json(path)
    except (OSError, ValueError, KeyError):
        return None


def parse_skills_input(text: str, vocab: SkillVocab | None) -> tuple[list[str], dict[str, list[str]]]:
    """Comma-separated skills -> (canonical skills, {unknown token: close suggestions}).
    Without a vocabulary (AI artifacts missing) cleaned tokens are accepted as they are."""
    known: set[str] = set()
    unknown: dict[str, list[str]] = {}
    synonyms = vocab.synonyms if vocab else {}
    for token in split_skills(text or ""):
        for s in expand_skill(token, synonyms):
            if not s:
                continue
            if vocab is None or s in vocab.canonical:
                known.add(s)
            else:
                unknown[s] = difflib.get_close_matches(s, sorted(vocab.canonical), n=3, cutoff=0.6)
    return sorted(known), unknown


def gate_date(internship: Internship):
    """Imported postings are judged against the dataset's last scrape day (D-007); others against today."""
    return REFERENCE_DATE if internship.source_id else timezone.localdate()


def internship_facts(internship: Internship) -> InternshipFacts:
    return InternshipFacts(
        id=internship.pk, status=internship.status, deadline=internship.application_deadline,
        required_qualification=internship.required_qualification, specialization=internship.specialization or None,
        minimum_academic_percentage=Decimal(internship.minimum_academic_percentage),
        required_skills=tuple(internship.required_skills or ()), text=internship.text_for_matching())


def requirements_open_to(qualification: str) -> list[str]:
    """Required-qualification values that a student with `qualification` satisfies (for search)."""
    return [req for req, accepted in QUALIFICATION_HIERARCHY.items() if qualification in accepted]
