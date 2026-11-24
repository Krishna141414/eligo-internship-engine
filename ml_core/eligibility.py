"""Eligibility gates (run BEFORE any similarity scoring) and assessment score maths.

Every gate returns a GateResult(gate, passed, reason). `evaluate_gates` runs all of them
and keeps every reason, so the UI can say exactly why an internship isn't open to a student.
Mandatory qualification and the >60% assessment rule are hard gates: no similarity score
can override them (spec §14).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import NamedTuple

from ml_core.config import PASS_THRESHOLD

# --- score maths -------------------------------------------------------------------------


def score_percentage(obtained: Decimal, total: Decimal) -> Decimal:
    """(obtained / total) × 100 as an unrounded Decimal. Round only when displaying."""
    obtained, total = Decimal(obtained), Decimal(total)
    if total <= 0:
        raise ValueError("Total marks must be greater than zero.")
    return obtained / total * Decimal(100)


def is_qualified(score: Decimal) -> bool:
    """True only when the score is strictly greater than 60 (exactly 60 is Not_Qualified)."""
    return Decimal(score) > PASS_THRESHOLD


def fmt_pct(value: Decimal) -> str:
    """Display helper: 2 decimal places, e.g. 60.00%."""
    return f"{Decimal(value).quantize(Decimal('0.01'))}%"


# --- qualification hierarchy (docs/DECISIONS.md D-017) ------------------------------------

UNDERGRADUATE: tuple[str, ...] = ("B.Tech", "B.Sc", "BCA", "B.Com", "BA", "BBA", "B.Des", "LLB")
POSTGRADUATE: tuple[str, ...] = ("M.Tech", "M.Sc", "MCA", "MBA", "M.Com", "MA")
#: Choices offered on the student profile form.
QUALIFICATIONS: tuple[str, ...] = ("Diploma",) + UNDERGRADUATE + POSTGRADUATE
#: Same-field postgraduate degree that also satisfies a specific undergraduate requirement.
PG_OF: dict[str, str] = {"B.Tech": "M.Tech", "B.Sc": "M.Sc", "BCA": "MCA", "B.Com": "M.Com",
                         "BA": "MA", "BBA": "MBA"}

ANY_GRADUATE = "Any Graduate"
ANY_POSTGRADUATE = "Any Postgraduate"


def _build_hierarchy() -> dict[str, frozenset[str]]:
    ug, pg = frozenset(UNDERGRADUATE), frozenset(POSTGRADUATE)
    h: dict[str, frozenset[str]] = {
        ANY_GRADUATE: ug | pg,
        ANY_POSTGRADUATE: pg,
        "Diploma": frozenset({"Diploma"}) | ug | pg,
    }
    for degree in UNDERGRADUATE:
        h[degree] = frozenset({degree} | ({PG_OF[degree]} if degree in PG_OF else set()))
    for degree in POSTGRADUATE:
        h[degree] = frozenset({degree})
    return h


#: required qualification -> set of student qualifications that satisfy it
QUALIFICATION_HIERARCHY: dict[str, frozenset[str]] = _build_hierarchy()
#: Values an internship's required_qualification may take.
REQUIRED_QUALIFICATIONS: tuple[str, ...] = (ANY_GRADUATE, ANY_POSTGRADUATE) + QUALIFICATIONS

#: Specialisations; a required group accepts its related fields.
SPECIALIZATIONS: tuple[str, ...] = ("CSE", "IT", "AI & ML", "Data Science", "ECE", "EEE",
                                    "Mechanical", "Civil", "Commerce", "Management", "Arts",
                                    "Science", "Law", "Design", "Other")
SPECIALIZATION_GROUPS: dict[str, frozenset[str]] = {
    "CSE": frozenset({"CSE", "IT", "AI & ML", "Data Science"}),
}


def is_blank(value: object) -> bool:
    """None, "", NaN (pandas missing value) and the strings "nan"/"none" all mean 'not set'."""
    if value is None:
        return True
    if isinstance(value, float) and value != value:   # NaN
        return True
    return str(value).strip().lower() in {"", "nan", "none"}


def accepts(required: str, student_qualification: str) -> bool:
    return student_qualification in QUALIFICATION_HIERARCHY.get(required, frozenset({required}))


# --- gates ---------------------------------------------------------------------------------


class GateResult(NamedTuple):
    gate: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class StudentFacts:
    qualification: str
    specialization: str
    academic_percentage: Decimal
    skills: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class InternshipFacts:
    id: object
    status: str
    deadline: date | None
    required_qualification: str
    specialization: str | None
    minimum_academic_percentage: Decimal
    required_skills: tuple[str, ...]
    text: str


@dataclass
class EligibilityResult:
    gates: list[GateResult] = field(default_factory=list)

    @property
    def failed(self) -> list[GateResult]:
        return [g for g in self.gates if not g.passed]

    @property
    def eligible(self) -> bool:
        return not self.failed


def check_status_and_deadline(status: str, deadline: date | None, today: date) -> GateResult:
    gate = "status_deadline"
    if status != "ACTIVE":
        return GateResult(gate, False, "This internship is not accepting applications right now.")
    if deadline is not None and deadline < today:
        return GateResult(gate, False, f"The application deadline ({deadline:%d %b %Y}) has passed.")
    if deadline is None:
        return GateResult(gate, True, "Open: no application deadline is listed.")
    return GateResult(gate, True, f"Open until {deadline:%d %b %Y}.")


def check_qualification(student_qualification: str, required: str) -> GateResult:
    gate = "qualification"
    if is_blank(required):
        required = ANY_GRADUATE
    if is_blank(student_qualification):
        return GateResult(gate, False, "Your profile is missing your qualification. Add it to check eligibility.")
    if accepts(required, student_qualification):
        return GateResult(gate, True, f"Your qualification ({student_qualification}) meets the requirement ({required}).")
    return GateResult(gate, False,
                      f"Requires {required}; your qualification is {student_qualification}.")


def check_specialization(student_specialization: str, required: str | None) -> GateResult:
    gate = "specialization"
    if is_blank(required):
        return GateResult(gate, True, "No specific specialisation required.")
    required = str(required).strip()
    accepted = SPECIALIZATION_GROUPS.get(required, frozenset({required}))
    if student_specialization in accepted:
        return GateResult(gate, True, f"Your specialisation ({student_specialization}) matches {required}.")
    shown = "not set in your profile" if is_blank(student_specialization) else student_specialization
    return GateResult(gate, False, f"Requires a {required}-related specialisation; yours is {shown}.")


def check_academic_percentage(student_pct: Decimal, minimum: Decimal) -> GateResult:
    gate = "academic_percentage"
    student_pct, minimum = Decimal(student_pct), Decimal(minimum)
    if student_pct >= minimum:
        return GateResult(gate, True, f"Your academic score {fmt_pct(student_pct)} meets the minimum {fmt_pct(minimum)}.")
    return GateResult(gate, False,
                      f"Requires at least {fmt_pct(minimum)} academics; yours is {fmt_pct(student_pct)}.")


def check_assessment(score: Decimal | None) -> GateResult:
    gate = "assessment"
    if score is None:
        return GateResult(gate, False,
                          "You haven't passed an assessment for your qualification yet. Take one to unlock recommendations.")
    if is_qualified(score):
        return GateResult(gate, True, f"Your assessment score {fmt_pct(score)} is above 60%.")
    return GateResult(gate, False,
                      f"Your assessment score {fmt_pct(score)} is not above 60%. Retake the assessment to qualify.")


def evaluate_gates(student: StudentFacts, internship: InternshipFacts,
                   assessment_score: Decimal | None, today: date) -> EligibilityResult:
    """Run every gate (no short-circuit) so all failure reasons can be shown together."""
    return EligibilityResult([
        check_status_and_deadline(internship.status, internship.deadline, today),
        check_qualification(student.qualification, internship.required_qualification),
        check_specialization(student.specialization, internship.specialization),
        check_academic_percentage(student.academic_percentage, internship.minimum_academic_percentage),
        check_assessment(assessment_score),
    ])
