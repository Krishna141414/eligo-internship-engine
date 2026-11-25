"""Skill normalisation shared by both datasets, the profile form and the LLM output (D-013).

One canonical vocabulary + one synonym map means "MS-Excel", "ms excel" and "Excel"
all become "excel" everywhere, so matched/missing skills don't silently miss on spelling.
"""
from __future__ import annotations

import functools
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

_SEPARATORS = re.compile(r"[,;/|\n]+")
_PLACEHOLDERS = {"", "nan", "none", "not available", "not specified", "nothing", "na", "n/a"}
_EDGE_PUNCT = " .,;:-_'\"()[]"
_EDGE_PUNCT_NO_BRACKETS = " .,;:-_'\"[]"

#: token (already lower-cased, whitespace-collapsed) -> canonical skill
BASE_SYNONYMS: dict[str, str] = {
    "js": "javascript", "java script": "javascript",
    "py": "python", "python3": "python",
    "ml": "machine learning", "machinelearning": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning", "deeplearning": "deep learning",
    "ms excel": "excel", "ms-excel": "excel", "microsoft excel": "excel",
    "ms word": "word", "ms-word": "word", "microsoft word": "word",
    "ms powerpoint": "powerpoint", "ms-powerpoint": "powerpoint", "ppt": "powerpoint",
    "ms office": "ms office", "ms-office": "ms office", "microsoft office": "ms office",
    "problemsolving": "problem solving", "problem-solving": "problem solving",
    "criticalthinking": "critical thinking",
    "nodejs": "node.js", "node js": "node.js",
    "reactjs": "react", "react.js": "react",
    "html5": "html", "css3": "css",
    "seo": "search engine optimization (seo)",
    "search engine optimization": "search engine optimization (seo)",
    "ui/ux": "ui/ux design", "ui ux": "ui/ux design", "ux/ui": "ui/ux design",
    "ui/ux design": "ui/ux design",
    "data visualisation": "data visualization",
    "cyber security": "cybersecurity",
}

#: Spelling variants found in the Student Career survey's own vocabulary (Phase 4 review of the
#: 268 model features, D-022). Each variant maps to the one canonical skill it clearly means.
SURVEY_SYNONYMS: dict[str, str] = {
    # adaptability / collaboration / communication
    "adaptability to new idea": "adaptability", "adaptable": "adaptability", "adaption": "adaptability",
    "collaborative learning": "collaboration", "collaborative practice": "collaboration",
    "collaborative working": "collaboration", "communications": "communication",
    "critical thought": "critical thinking",
    "interpersonal skill": "interpersonal skills", "interpersonal skils": "interpersonal skills",
    "interpersonalskills": "interpersonal skills", "interpersonnal skills": "interpersonal skills",
    "problem solution": "problem solving", "problem solver": "problem solving",
    "problem solving & analysis": "problem solving", "problem solving and analysis": "problem solving",
    "problem solving and analyzing": "problem solving", "problemsolution": "problem solving",
    "problemsolving & analyzing": "problem solving", "problemsolving and analysis": "problem solving",
    "projectmanagement": "project management",
    # development
    "android app develop": "android app development", "android app developing": "android app development",
    "android app make": "android app development", "android application develop": "android app development",
    "mobile app develop": "mobile app development", "mobile application development": "mobile app development",
    "mobile apps development": "mobile app development", "mobileapp development": "mobile app development",
    "game develop": "game development", "games development": "game development",
    "web based project develop": "web development", "web based project developing": "web development",
    "web based projectdevelop": "web development", "web based projects develop": "web development",
    "web basedproject develop": "web development",
    "website build": "website development", "website builders": "website development",
    "website building": "website development",
    "systems design": "system design",
    "api testers": "api testing", "api testings": "api testing",
    # data / AI
    "artificial intelligence (ai)": "artificial intelligence", "artificialintelligence (ai)": "artificial intelligence",
    "working with machine learning": "machine learning",
    "big data technlogs": "big data technologies", "big data technology": "big data technologies",
    "data analyst": "data analytics", "data engineer": "data engineering", "dataengineering": "data engineering",
    "data sciences": "data science", "data scientist": "data science",
    "data structure": "data structures",
    "database developement": "database development", "database developer": "database development",
    "database developers": "database development", "database developing": "database development",
    "database developments": "database development",
    "db management": "databases", "dbms": "databases",
    "feature enginge": "feature engineering", "features engineering": "feature engineering",
    "features engagement": "feature engagement",
    "statistic analysis": "statistical analysis", "statistical analyses": "statistical analysis",
    "statistical analytics": "statistical analysis", "statistician": "statistics", "statisticians": "statistics",
    "research on artificial intelligence & machine learning": "research on artificial intelligence and machine learning",
    "research on artificial intelligence and machinelearning": "research on artificial intelligence and machine learning",
    "research on artificial intelligence andmachine learning": "research on artificial intelligence and machine learning",
    # security / networks / systems
    "cybersec": "cybersecurity", "research on cyberspace": "research on cyber security",
    "cryptograph": "cryptography", "cryptographic mechanisms": "cryptography",
    "cryptographic technologies": "cryptography", "cryptographic tools": "cryptography", "cryptology": "cryptography",
    "computer network": "computer networks", "networm": "computer networks",
    "network topologies": "network topology", "network topology analyzed": "network topology",
    "operating systems and networkings": "operating systems and networking",
    "operting systems and networking": "operating systems and networking", "operting systems": "operating systems",
    "cloud": "cloud computing", "cloud technology": "cloud computing",
    "block chain": "blockchain", "blockchain technology": "blockchain", "blockchains": "blockchain",
    "research on block chain": "research on blockchain",
    "iot": "internet of things", "working with iot": "internet of things",
    "robotics knowhow": "robotics knowledge", "robotics knowledges": "robotics knowledge",
    "work with robotics": "working with robotics", "working with robots": "working with robotics",
    "research on robots": "research on robotics",
    "telecommunication": "telecommunications",
    # testing / QA
    "software qa": "software quality assurance", "software quality assurance course": "software quality assurance",
    "software quality testing": "software quality assurance",
    "software testing related work": "software testing", "software testing relatedwork": "software testing",
    # design / media
    "graphicdesign": "graphic design", "illustration & design": "illustration and design",
    "image managements": "image management",
    "ui/ux knowledge": "ui/ux design", "ui/ux related job": "ui/ux design", "ux": "ui/ux design",
    "ux knowledge": "ui/ux design", "ux/ui knowledge": "ui/ux design",
    "social media manage": "social media management", "social media manager": "social media management",
    "search engine optimization(seo)": "search engine optimization (seo)",
    "ar": "augmented reality", "participation in ar": "augmented reality",
    # misc
    "coding bootcamps and workshop": "coding bootcamps and workshops",
    "teaching assistantships (tas)": "teaching",
    "work with new idea": "innovation", "working with new concept": "innovation", "working with new idea": "innovation",
    "working with new ideas": "innovation", "working withnew idea": "innovation",
    "work with technology and new idea generate": "innovation",
    "working with technology and new idea generate": "innovation",
    "working with technology and new idea generation": "innovation",
    "working with technology": "technology",
}
BASE_SYNONYMS.update(SURVEY_SYNONYMS)

#: compound tokens -> several canonical skills (real Student Career strings)
SPLIT_MAP: dict[str, tuple[str, ...]] = {
    "artifical intelligence (ai) and machine learning": ("artificial intelligence", "machine learning"),
    "artificial intelligence (ai) & machine learning": ("artificial intelligence", "machine learning"),
    "game develop} artificial intelligence (ai) and machine learning": (
        "game development", "artificial intelligence", "machine learning"),
    "data analysis & visualization": ("data analysis", "data visualization"),
    "data analysis and visulaization": ("data analysis", "data visualization"),
    "problem solving and communication": ("problem solving", "communication"),
    "problemsolving and leadership": ("problem solving", "leadership"),
    "video editing & animation": ("video editing", "animation"),
    "video editing and animation": ("video editing", "animation"),
    "vr and game dev lab": ("virtual reality", "game development"),
    "content writing and blogging": ("content writing", "blogging"),
    "artificial intelligence (ai) and machine learning": ("artificial intelligence", "machine learning"),
    "artificial intelligence and machine learning": ("artificial intelligence", "machine learning"),
    "data analysis and visualization": ("data analysis", "data visualization"),
    "data analysis andvisualization": ("data analysis", "data visualization"),
    "data analysis and visualisation": ("data analysis", "data visualization"),
}


def split_skills(text: str) -> list[str]:
    """Split a skills string on , ; / | and newlines; drop empty and placeholder values.

    "UI/UX" style tokens are protected so the slash inside them doesn't split.
    """
    if text is None:
        return []
    protected = re.sub(r"\b(ui|ux)\s*/\s*(ux|ui)\b", lambda m: f"{m.group(1)}\x00{m.group(2)}",
                       str(text), flags=re.I)
    parts = [p.replace("\x00", "/").strip() for p in _SEPARATORS.split(protected)]
    return [p for p in parts if p.strip(_EDGE_PUNCT).lower() not in _PLACEHOLDERS]


def _clean(token: str) -> str:
    """Lower-case, collapse whitespace, trim edge punctuation. Brackets are only trimmed when they
    are unbalanced or wrap the whole token, so "English Proficiency (Spoken)" keeps its ")"."""
    s = re.sub(r"\s+", " ", str(token).lower()).strip(_EDGE_PUNCT_NO_BRACKETS)
    while s.startswith("(") and s.endswith(")") and s.count("(") == 1:
        s = s[1:-1].strip(_EDGE_PUNCT_NO_BRACKETS)
    if s.endswith(")") and s.count("(") < s.count(")"):
        s = s[:-1]
    if s.startswith("(") and s.count("(") > s.count(")"):
        s = s[1:]
    return s.strip(_EDGE_PUNCT_NO_BRACKETS).strip()


def normalise_skill(token: str, synonyms: Mapping[str, str]) -> str:
    """Lower-case, collapse whitespace, trim edge punctuation, then apply the synonym map."""
    cleaned = _clean(token)
    return synonyms.get(cleaned, cleaned)


def expand_skill(token: str, synonyms: Mapping[str, str]) -> list[str]:
    """Like normalise_skill, but compound tokens expand to several canonical skills."""
    cleaned = _clean(token)
    if cleaned in SPLIT_MAP:
        return [synonyms.get(s, s) for s in SPLIT_MAP[cleaned]]
    return [synonyms.get(cleaned, cleaned)]


@dataclass(frozen=True)
class SkillVocab:
    canonical: frozenset[str]
    synonyms: Mapping[str, str] = field(default_factory=lambda: dict(BASE_SYNONYMS))

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, SkillVocab) and self.canonical == other.canonical
                and dict(self.synonyms) == dict(other.synonyms))

    def __hash__(self) -> int:
        return hash(self.canonical)

    @classmethod
    def build(cls, token_lists: Iterable[Iterable[str]], synonyms: Mapping[str, str],
              min_count: int = 1) -> "SkillVocab":
        counts: Counter[str] = Counter()
        for tokens in token_lists:
            for t in tokens:
                for s in expand_skill(t, synonyms):
                    if s:
                        counts[s] += 1
        return cls(frozenset(s for s, c in counts.items() if c >= min_count), dict(synonyms))

    def to_json(self, path: Path) -> None:
        Path(path).write_text(json.dumps({"canonical": sorted(self.canonical),
                                          "synonyms": dict(sorted(self.synonyms.items()))},
                                         indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> "SkillVocab":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(frozenset(data["canonical"]), dict(data["synonyms"]))


def normalise_skills(value: str | Iterable[str], vocab: SkillVocab) -> list[str]:
    """Canonical, sorted, de-duplicated skills that exist in the vocabulary."""
    tokens = split_skills(value) if isinstance(value, str) else list(value)
    out = set()
    for t in tokens:
        for s in expand_skill(t, vocab.synonyms):
            if s in vocab.canonical:
                out.add(s)
    return sorted(out)


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9+#])")


@functools.lru_cache(maxsize=8)
def _phrase_table(vocab: SkillVocab) -> tuple[tuple[str, str, re.Pattern[str]], ...]:
    """(phrase, canonical skill, compiled pattern), longest phrase first. Cached per vocabulary."""
    phrases: dict[str, str] = {s: s for s in vocab.canonical}
    for alias, target in vocab.synonyms.items():
        if target in vocab.canonical and len(alias) >= 2:
            phrases.setdefault(alias, target)
    return tuple((p, phrases[p], _phrase_pattern(p)) for p in sorted(phrases, key=len, reverse=True))


def extract_skills_rule_based(free_text: str, vocab: SkillVocab) -> list[str]:
    """Deterministic extraction from free text: longest phrase first, word boundaries,
    synonyms included. Matched spans are masked so "learning" isn't found inside
    "machine learning"."""
    text = " " + re.sub(r"\s+", " ", str(free_text or "").lower()) + " "
    found: set[str] = set()
    for phrase, target, pattern in _phrase_table(vocab):
        if phrase in text and pattern.search(text):
            found.add(target)
            text = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return sorted(found)


@dataclass
class SkillComparison:
    matched: list[str]
    missing: list[str]
    extra: list[str]


def compare_skills(student: Iterable[str], required: Iterable[str]) -> SkillComparison:
    s, r = set(student), set(required)
    return SkillComparison(matched=sorted(s & r), missing=sorted(r - s), extra=sorted(s - r))


class SkillBinarizer(BaseEstimator, TransformerMixin):
    """Multi-hot encoder over canonical skills (D-012).

    The vocabulary is learned in `fit` from the training rows only (leakage-safe), keeping
    skills that appear in at least `min_count` rows. Unknown skills at transform time are ignored.
    Input: a sequence of skill lists (already normalised).
    """

    def __init__(self, min_count: int = 2):
        self.min_count = min_count

    def fit(self, X: Sequence[Iterable[str]], y=None) -> "SkillBinarizer":
        counts: Counter[str] = Counter()
        for row in X:
            counts.update(set(row))
        self.vocabulary_ = np.array(sorted(s for s, c in counts.items() if c >= self.min_count), dtype=object)
        self._index = {s: i for i, s in enumerate(self.vocabulary_)}
        return self

    def transform(self, X: Sequence[Iterable[str]]) -> np.ndarray:
        out = np.zeros((len(X), len(self.vocabulary_)), dtype=np.int8)
        index = getattr(self, "_index", None) or {s: i for i, s in enumerate(self.vocabulary_)}
        for r, row in enumerate(X):
            for s in set(row):
                j = index.get(s)
                if j is not None:
                    out[r, j] = 1
        return out

    def get_feature_names_out(self, input_features=None) -> np.ndarray:
        return np.array([f"skill__{s}" for s in self.vocabulary_], dtype=object)
