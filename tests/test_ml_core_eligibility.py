"""Tests for ml_core.eligibility: score maths, the >60% rule, qualification hierarchy, gates."""
from datetime import date
from decimal import Decimal

import pytest

from ml_core.config import REFERENCE_DATE
from ml_core.eligibility import (
    InternshipFacts,
    StudentFacts,
    check_academic_percentage,
    check_assessment,
    check_qualification,
    check_specialization,
    check_status_and_deadline,
    evaluate_gates,
    is_qualified,
    score_percentage,
)


# --- score maths -----------------------------------------------------------------
@pytest.mark.parametrize(
    "obtained,total,expected",
    [
        (3, 5, False),                                    # exactly 60%
        (Decimal("60.01"), 100, True),                    # 60.01%
        (100, 100, True),                                 # 100%
        (0, 100, False),                                  # 0%
        (Decimal("6001"), Decimal("10000"), True),        # 60.01% from integer marks
        (Decimal("5999"), Decimal("10000"), False),       # 59.99%
    ],
)
def test_is_qualified_boundary(obtained, total, expected):
    assert is_qualified(score_percentage(Decimal(obtained), Decimal(total))) is expected


def test_exactly_sixty_is_not_qualified():
    assert is_qualified(Decimal("60.00")) is False


def test_score_percentage_zero_total_raises():
    with pytest.raises(ValueError):
        score_percentage(Decimal(0), Decimal(0))


def test_score_percentage_is_unrounded():
    # 2/3 = 66.666...%; rounding to 2 dp must not happen in the stored value
    assert score_percentage(Decimal(2), Decimal(3)) == Decimal(2) / Decimal(3) * 100


def test_tiny_margin_above_sixty_qualifies_even_if_display_rounds_to_60():
    # 60.004% displays as 60.00 but is strictly above 60 -> Qualified (rule: round only for display)
    assert is_qualified(score_percentage(Decimal("60004"), Decimal("100000"))) is True


# --- qualification hierarchy --------------------------------------------------------
@pytest.mark.parametrize(
    "student,required,ok",
    [
        ("B.Tech", "Any Graduate", True),
        ("BCA", "Any Graduate", True),
        ("Diploma", "Any Graduate", False),
        ("M.Tech", "B.Tech", True),
        ("B.Sc", "B.Tech", False),
        ("MBA", "Any Postgraduate", True),
        ("B.Com", "Any Postgraduate", False),
        ("B.Tech", "Diploma", True),
        ("MCA", "BCA", True),
        ("BCA", "MCA", False),
    ],
)
def test_qualification_hierarchy(student, required, ok):
    assert check_qualification(student, required).passed is ok


def test_qualification_failure_reason_names_both():
    r = check_qualification("Diploma", "Any Graduate")
    assert "Any Graduate" in r.reason and "Diploma" in r.reason


def test_missing_student_qualification_fails_with_profile_hint():
    r = check_qualification("", "Any Graduate")
    assert not r.passed and "profile" in r.reason.lower()


# --- specialization -------------------------------------------------------------------
def test_specialization_none_required_passes():
    assert check_specialization("CSE", None).passed
    assert check_specialization("", "").passed


@pytest.mark.parametrize("blank", [None, "", float("nan"), "nan", "None"])
def test_specialization_blank_values_mean_no_requirement(blank):
    # pandas 3 turns missing strings into NaN; that must not become a "nan" requirement
    r = check_specialization("CSE", blank)
    assert r.passed and "nan" not in r.reason.lower()


def test_specialization_group_accepts_related_fields():
    assert check_specialization("AI & ML", "CSE").passed
    assert not check_specialization("Mechanical", "CSE").passed


# --- academic percentage ----------------------------------------------------------------
def test_academic_percentage_at_minimum_passes():
    assert check_academic_percentage(Decimal("60"), Decimal("60")).passed
    assert not check_academic_percentage(Decimal("59.99"), Decimal("60")).passed


# --- status and deadline ------------------------------------------------------------------
def test_deadline_passed_fails_with_reason():
    r = check_status_and_deadline("ACTIVE", date(2025, 9, 27), REFERENCE_DATE)
    assert not r.passed and "deadline" in r.reason.lower()


def test_deadline_today_still_open():
    assert check_status_and_deadline("ACTIVE", REFERENCE_DATE, REFERENCE_DATE).passed


def test_no_deadline_passes():
    assert check_status_and_deadline("ACTIVE", None, REFERENCE_DATE).passed


def test_inactive_fails():
    assert not check_status_and_deadline("INACTIVE", None, REFERENCE_DATE).passed


# --- assessment -------------------------------------------------------------------------
def test_assessment_missing_fails_with_cta_reason():
    r = check_assessment(None)
    assert not r.passed and "assessment" in r.reason.lower()


def test_assessment_sixty_fails_and_reason_shows_score():
    r = check_assessment(Decimal("60"))
    assert not r.passed and "60.00%" in r.reason


def test_assessment_above_sixty_passes():
    assert check_assessment(Decimal("60.01")).passed


# --- all gates ------------------------------------------------------------------------
def _student(**kw):
    base = dict(qualification="B.Tech", specialization="CSE", academic_percentage=Decimal("75"),
                skills=("python",), text="python")
    base.update(kw)
    return StudentFacts(**base)


def _internship(**kw):
    base = dict(id=1, status="ACTIVE", deadline=None, required_qualification="Any Graduate",
                specialization=None, minimum_academic_percentage=Decimal("0"),
                required_skills=("python",), text="python intern")
    base.update(kw)
    return InternshipFacts(**base)


def test_evaluate_gates_all_pass():
    result = evaluate_gates(_student(), _internship(), Decimal("72.5"), REFERENCE_DATE)
    assert result.eligible and result.failed == []
    assert {g.gate for g in result.gates} == {"status_deadline", "qualification", "specialization",
                                              "academic_percentage", "assessment"}


def test_evaluate_gates_collects_all_failures():
    student = _student(qualification="Diploma", academic_percentage=Decimal("40"))
    internship = _internship(required_qualification="B.Tech", minimum_academic_percentage=Decimal("60"))
    result = evaluate_gates(student, internship, Decimal("55"), REFERENCE_DATE)
    assert not result.eligible
    assert {g.gate for g in result.failed} == {"qualification", "academic_percentage", "assessment"}
