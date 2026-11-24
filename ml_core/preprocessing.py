"""Cleaning and feature-text builders for both datasets (spec §2).

Every rule here is documented in docs/DATASETS.md and docs/DECISIONS.md (D-007). Values that come
from a rule or a default instead of the source are listed per record in `derived_fields`.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd

from ml_core.eligibility import ANY_GRADUATE, ANY_POSTGRADUATE, POSTGRADUATE
from ml_core.skills import SkillVocab, normalise_skills

_PLACEHOLDERS = {"not available", "not specified", "nothing", "nan", "none", "n/a", "na", ""}
_TAG = re.compile(r"<[^>]+>")


def clean_text(text: object) -> str:
    """Strip HTML tags/entities, collapse whitespace; placeholders become ""."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = html.unescape(_TAG.sub(" ", str(text))).replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return "" if s.lower() in _PLACEHOLDERS else s


# --- stipend / duration / deadline ---------------------------------------------------------


@dataclass
class StipendRange:
    min_inr: int | None
    max_inr: int | None
    unpaid: bool
    text: str


def parse_stipend(text: str) -> StipendRange:
    t = clean_text(text)
    if not t:
        return StipendRange(None, None, False, "")
    if t.lower().startswith("unpaid"):
        return StipendRange(0, 0, True, t)
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", t)]
    if not nums:
        return StipendRange(None, None, False, t)
    return StipendRange(nums[0], nums[1] if len(nums) > 1 else nums[0], False, t)


_DURATION = re.compile(r"^(\d+(?:\.\d+)?)\s+(month|months|week|weeks)$", re.I)


def parse_duration_months(text: str) -> float | None:
    m = _DURATION.match(clean_text(text))
    if not m:
        return None
    n = float(m.group(1))
    return n if m.group(2).lower().startswith("month") else n / 4


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_DEADLINE = re.compile(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*'?\s*(\d{2,4})?")


def parse_deadline(text: str, year_hint: int = 2025) -> date | None:
    """"15 Oct' 25" -> 2025-10-15. Unparseable or impossible dates -> None."""
    m = _DEADLINE.search(clean_text(text))
    if not m or m.group(2).lower() not in _MONTHS:
        return None
    year = int(m.group(3)) if m.group(3) else year_hint
    if year < 100:
        year += 2000
    try:
        return date(year, _MONTHS[m.group(2).lower()], int(m.group(1)))
    except ValueError:
        return None


# --- education -> qualification (D-007) -------------------------------------------------------


@dataclass
class QualificationRule:
    required_qualification: str
    specialization: str | None
    derived: bool
    note: str


#: (regex, qualification). Order doesn't matter; all matches are collected.
_DEGREE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bb\.?\s?tech\b|\bb\.?\s?e\.(?!g)|\bbachelor of engineering\b|\bengineering (?:degree|graduate|students?)\b", "B.Tech"),
    (r"\bm\.?\s?tech\b|\bm\.?\s?e\.(?!g)", "M.Tech"),
    (r"\bbca\b", "BCA"), (r"\bmca\b", "MCA"),
    (r"\bbba\b", "BBA"), (r"\bmba\b|\bpgdm\b", "MBA"),
    (r"\bb\.?\s?sc\b", "B.Sc"), (r"\bm\.?\s?sc\b", "M.Sc"),
    (r"\bb\.?\s?com\b", "B.Com"), (r"\bm\.?\s?com\b", "M.Com"),
    (r"\bllb\b|\bll\.b\b", "LLB"), (r"\bb\.?\s?des\b", "B.Des"),
)
_COMMERCE_UG = r"\bbaf\b|\bbms\b|\bbbm\b"   # real commerce UG degrees outside our list -> treated as generic
_DIPLOMA = r"\bdiploma\b"
_PG_GENERIC = r"\bpost\s?-?graduat|\bmaster[’']s\b|\bmasters\b|\bmaster(?:'s|’s)?\s+(?:degree|of)\b|\bph\.?\s?d\b"
#: Text that opens the internship to people without a specific degree -> never restrict.
_OPEN_TO_ALL = r"\bfreshers?\b|\bany (?:stream|discipline|graduate|degree)\b|\ball streams?\b|\bfrom any\b"
_STUDY_WORDS = r"degree|diploma|bachelor|master|graduat|enrolled|pursuing|background|student|stream|discipline"
_CSE = r"computer science|computer engineering|software engineering|software\b|information technology|\bcse\b"


def parse_education(text: str) -> QualificationRule:
    """Rule-based mapping of Internshala's free-text `Education` field (D-007).

    Not specified / not about education (e.g. "are from Mumbai only") -> "Any Graduate",
    with the original text kept as an eligibility note.
    """
    note = clean_text(text)
    if not note:
        return QualificationRule(ANY_GRADUATE, None, True, "")
    low = note.lower()
    specifics = {q for pattern, q in _DEGREE_PATTERNS if re.search(pattern, low)}
    commerce_generic = bool(re.search(_COMMERCE_UG, low))
    about_study = bool(re.search(_STUDY_WORDS, low)) or bool(specifics)

    if re.search(_OPEN_TO_ALL, low):
        qualification = ANY_GRADUATE
    elif re.search(_DIPLOMA, low) and about_study:
        qualification = "Diploma"
    elif len(specifics) == 1 and not commerce_generic:
        qualification = next(iter(specifics))
    elif specifics and all(q in POSTGRADUATE for q in specifics):
        qualification = ANY_POSTGRADUATE
    elif specifics or commerce_generic:
        qualification = ANY_GRADUATE
    elif re.search(_PG_GENERIC, low) and not re.search(r"bachelor", low):
        qualification = ANY_POSTGRADUATE
    else:
        qualification = ANY_GRADUATE

    specialization = None
    if about_study and (re.search(_CSE, low) or re.search(r"\bIT\b", note)):
        specialization = "CSE"
    return QualificationRule(qualification, specialization, True, note)


# --- misc builders ------------------------------------------------------------------------------


def work_mode_from_location(location: str) -> str:
    loc = clean_text(location)
    if not loc:
        return ""
    return "Remote" if "work from home" in loc.lower() else "On-site"


def build_internship_text(title: str, role: str, skills: Iterable[str], education_note: str,
                          perks: str, description: str = "") -> str:
    """Text used by TF-IDF and the sentence model for an internship."""
    parts: list[str] = []
    for p in (clean_text(title), clean_text(role)):
        if p and p not in parts:
            parts.append(p)
    skills = list(skills)
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    for p in (clean_text(education_note), clean_text(perks), clean_text(description)):
        if p:
            parts.append(p)
    return ". ".join(parts)


def build_student_text(skills: Iterable[str], career_interests: str, preferred_job_role: str,
                       specialization: str) -> str:
    """Text used by TF-IDF and the sentence model for a student profile."""
    parts: list[str] = []
    skills = list(skills)
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    for label, value in (("Interests", career_interests), ("Preferred role", preferred_job_role),
                         ("Specialisation", specialization)):
        v = clean_text(value)
        if v:
            parts.append(f"{label}: {v}")
    return ". ".join(parts)


# --- dataset-level cleaning -------------------------------------------------------------------


def _composed_description(title: str, company: str, skills: list[str], perks: str, note: str) -> str:
    bits = [f"{title} internship at {company}." if company else f"{title} internship."]
    if skills:
        bits.append("Required skills: " + ", ".join(skills) + ".")
    if note:
        bits.append("Eligibility: " + note + ("" if note.endswith(".") else "."))
    if perks:
        bits.append("Perks: " + perks + ".")
    return " ".join(bits)


def clean_internships(raw: pd.DataFrame, vocab: SkillVocab) -> pd.DataFrame:
    """Kaggle 'Internship Opportunities in India (2025)' -> Eligo internship table.

    Drops rows with no title (`profile == "Nothing"`) and rows whose columns are shifted
    (`Start Date` longer than 40 chars). The `Offer` column ("Nothing" on every row) is dropped.
    """
    df = raw.copy()
    df = df[df["profile"].map(clean_text) != ""]
    df = df[df["Start Date"].astype(str).str.len() <= 40]

    records = []
    for _, r in df.iterrows():
        derived = ["description", "minimum_academic_percentage"]
        title = clean_text(r["profile"])
        company = clean_text(r["company"])
        skills = normalise_skills(str(r["Skills"]), vocab)
        rule = parse_education(r["Education"])
        derived.append("required_qualification")
        if rule.specialization:
            derived.append("specialization")
        perks = clean_text(r["Perks"])
        stipend = parse_stipend(r["Stipend"])
        months = parse_duration_months(r["Duration"])
        duration_text = clean_text(r["Duration"]) if months is not None else ""
        if months is None:
            derived.append("duration")
        location = clean_text(r["Location"])
        start = clean_text(r["Start Date"])
        criteria = "; ".join(p for p in (rule.note, f"Start: {start}" if start else "") if p)
        description = _composed_description(title, company, skills, perks, rule.note)
        records.append({
            "source_id": str(r["internship_id"]),
            "company_name": company,
            "internship_title": title,
            "job_role": title,
            "description": description,
            "description_derived": True,
            "required_qualification": rule.required_qualification,
            "specialization": rule.specialization,
            "minimum_academic_percentage": 0,
            "required_skills": skills,
            "required_skills_text": ", ".join(skills),
            "location": location,
            "work_mode": work_mode_from_location(r["Location"]),
            "stipend_text": stipend.text,
            "stipend_min": stipend.min_inr,
            "stipend_max": stipend.max_inr,
            "duration_text": duration_text,
            "duration_months": months,
            "application_deadline": parse_deadline(r["Apply by Date"]),
            "eligibility_criteria": criteria,
            "derived_fields": derived,
            "text": build_internship_text(title, title, skills, rule.note, perks),
        })
    return pd.DataFrame.from_records(records)


def clean_job_role_data(raw: pd.DataFrame, vocab: SkillVocab) -> pd.DataFrame:
    """Student Career dataset -> (skills, career). Exact duplicates are removed before any
    train/test split (and again after normalisation); rows with no known skill are dropped."""
    df = raw.drop_duplicates().copy()
    out = pd.DataFrame({
        "skills": df["Skill"].map(lambda s: normalise_skills(str(s), vocab)),
        "career": df["Career"].map(lambda c: clean_text(c)),
    })
    out = out[out["skills"].map(len) > 0]
    key = out["skills"].map(tuple)
    out = out[~pd.DataFrame({"k": key, "c": out["career"]}).duplicated()]
    return out.reset_index(drop=True)
