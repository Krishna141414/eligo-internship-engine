"""Tests for ml_core.preprocessing.

The `raw_sample` fixture is a TEST FIXTURE in the real Kaggle column format (values modelled on
real rows, including the real data-quality problems). It is not training data.
"""
from datetime import date

import pandas as pd
import pytest

from ml_core.preprocessing import (
    build_internship_text,
    build_student_text,
    clean_internships,
    clean_job_role_data,
    clean_text,
    parse_deadline,
    parse_duration_months,
    parse_education,
    parse_stipend,
    work_mode_from_location,
)
from ml_core.skills import BASE_SYNONYMS, SkillVocab

COLS = ["internship_id", "Date Time", "profile", "company", "Location", "Start Date", "Stipend",
        "Duration", "Apply by Date", "Offer", "Education", "Skills", "Perks"]


def _row(i, profile="Data Science", company="Acme Analytics", location="Bangalore", start="Immediately",
         stipend="₹ 10,000 - 15,000 /month", duration="3 Months", apply_by="15 Oct' 25",
         education="Not Specified", skills="Python, SQL, MS-Excel", perks="Certificate, Flexible"):
    return [f"2025TEST{i:04d}", "2025-09-27 20:41:17", profile, company, location, start, stipend,
            duration, apply_by, "Nothing", education, skills, perks]


@pytest.fixture
def vocab():
    return SkillVocab.build([["python", "sql", "excel", "digital marketing", "social media marketing",
                              "machine learning"]], BASE_SYNONYMS)


@pytest.fixture
def raw_sample():
    rows = [
        _row(1),
        _row(2, profile="Digital Marketing", company="Brand Scale-Up Inc", location="Work from home",
             skills="Digital Marketing, Social Media Marketing", stipend="₹ 5,000 /month"),
        _row(3, profile="Nothing", company="Ghost Co", location="Not Available"),           # no title -> drop
        _row(4, start="Goldman Sachs, founded in 1869 by Marcus Goldman, is a leading global investment bank"),  # shifted -> drop
        _row(5, company="Acme Labs", duration="1 week ago"),                                 # bad duration
        _row(6, skills="Not Available", stipend="Unpaid", apply_by="Not Available"),
        _row(7, company="Acme Software", education="1. Candidates currently enrolled in a degree/diploma in computer science/software/IT-related fields will only be hired."),
        _row(8, education="4. are from Mumbai only", stipend="Not Available"),
    ]
    return pd.DataFrame(rows, columns=COLS)


# --- small parsers ------------------------------------------------------------------------
def test_clean_text_strips_html_and_placeholders():
    assert clean_text("<p>Hello&nbsp;  <b>world</b></p>") == "Hello world"
    assert clean_text("Not Available") == ""
    assert clean_text("Nothing") == ""


@pytest.mark.parametrize("s,exp", [
    ("₹ 10,000 - 15,000 /month", (10000, 15000, False)),
    ("₹ 5,000 /month", (5000, 5000, False)),
    ("Unpaid", (0, 0, True)),
    ("Not Available", (None, None, False)),
])
def test_parse_stipend(s, exp):
    r = parse_stipend(s)
    assert (r.min_inr, r.max_inr, r.unpaid) == exp


@pytest.mark.parametrize("s,exp", [("3 Months", 3.0), ("1 Month", 1.0), ("2 Weeks", 0.5),
                                   ("1 Week", 0.25), ("1 week ago", None), ("Not Available", None)])
def test_parse_duration(s, exp):
    assert parse_duration_months(s) == exp


def test_parse_deadline():
    assert parse_deadline("15 Oct' 25") == date(2025, 10, 15)
    assert parse_deadline("2 Oct' 25") == date(2025, 10, 2)
    assert parse_deadline("Not Available") is None
    assert parse_deadline("31 Feb' 25") is None


def test_parse_education_not_specified():
    r = parse_education("Not Specified")
    assert r.required_qualification == "Any Graduate" and r.specialization is None and r.derived


def test_parse_education_cs_degree():
    r = parse_education("1. Candidates currently enrolled in a degree/diploma in computer "
                        "science/software/IT-related fields will only be hired.")
    assert r.specialization == "CSE"
    assert r.required_qualification == "Diploma"   # "degree/diploma": a diploma is enough


def test_parse_education_single_specific_degree():
    assert parse_education("1. B.Tech with CEH/CHFI will be preferable").required_qualification == "B.Tech"


def test_parse_education_several_degrees_is_any_graduate():
    r = parse_education("Commerce students (B.Com, BAF, BMS, BBA) can apply")
    assert r.required_qualification == "Any Graduate"


def test_parse_education_postgraduate():
    assert parse_education("Enrolled in an advanced graduate degree program (e.g., MBA, PhD)") \
        .required_qualification == "MBA"


def test_parse_education_location_limit_is_note_only():
    r = parse_education("4. are from Mumbai only")
    assert r.required_qualification == "Any Graduate" and r.specialization is None and "Mumbai" in r.note


def test_parse_education_master_as_verb_is_not_postgraduate():
    # real row: "4. Master the art of AI sales execution for different industries"
    assert parse_education("4. Master the art of AI sales execution").required_qualification == "Any Graduate"


def test_parse_education_masters_degree_is_postgraduate():
    # real row uses a curly apostrophe
    assert parse_education("1. Master’s degree in clinical psychology").required_qualification == "Any Postgraduate"


def test_parse_education_open_to_freshers_is_not_restricted_to_degree():
    # real row: "1. Freshers, students, freelancers, or MBA sales and marketing candidates."
    r = parse_education("1. Freshers, students, freelancers, or MBA sales and marketing candidates.")
    assert r.required_qualification == "Any Graduate"


def test_parse_education_it_pronoun_is_not_cse():
    r = parse_education("2. Make it happen with energy and drive")
    assert r.specialization is None


def test_work_mode():
    assert work_mode_from_location("Work from home") == "Remote"
    assert work_mode_from_location("Mumbai") == "On-site"
    assert work_mode_from_location("Not Available") == ""


def test_build_texts_contain_fields():
    t = build_internship_text("Data Science", "Data Science", ["python", "sql"], "", "Certificate")
    assert "python" in t and "sql" in t and t.count("Data Science") == 1
    s = build_student_text(["python"], "AI research", "Data Scientist", "CSE")
    assert "python" in s and "AI research" in s and "Data Scientist" in s


# --- clean_internships ------------------------------------------------------------------------
def test_clean_internships_drops_titleless_and_shifted_rows(raw_sample, vocab):
    out = clean_internships(raw_sample, vocab)
    assert list(out.source_id) == ["2025TEST0001", "2025TEST0002", "2025TEST0005", "2025TEST0006",
                                   "2025TEST0007", "2025TEST0008"]


def test_clean_internships_offer_column_dropped(raw_sample, vocab):
    assert "Offer" not in clean_internships(raw_sample, vocab).columns


def test_clean_internships_descriptions_composed_and_flagged(raw_sample, vocab):
    out = clean_internships(raw_sample, vocab)
    assert out.description_derived.all()
    assert all("description" in d for d in out.derived_fields)


def test_clean_internships_min_pct_default_zero_flagged(raw_sample, vocab):
    out = clean_internships(raw_sample, vocab)
    assert (out.minimum_academic_percentage == 0).all()
    assert all("minimum_academic_percentage" in d for d in out.derived_fields)


def test_clean_internships_skills_normalised(raw_sample, vocab):
    out = clean_internships(raw_sample, vocab).set_index("source_id")
    assert out.loc["2025TEST0001", "required_skills"] == ["excel", "python", "sql"]
    assert out.loc["2025TEST0006", "required_skills"] == []


def test_clean_internships_bad_duration_flagged(raw_sample, vocab):
    row = clean_internships(raw_sample, vocab).set_index("source_id").loc["2025TEST0005"]
    assert row.duration_months is None or pd.isna(row.duration_months)
    assert row.duration_text == "" and "duration" in row.derived_fields


def test_clean_internships_text_rebuildable_from_stored_fields(raw_sample, vocab):
    # Django stores title, job_role, required_skills and description (no perks/education columns);
    # it must be able to rebuild exactly the text the notebook embedded (D-014 text-hash check).
    for _, row in clean_internships(raw_sample, vocab).iterrows():
        assert row.text == build_internship_text(row.internship_title, row.job_role, row.required_skills,
                                                 "", "", row.description)
        assert "Perks:" in row.description or "Certificate" not in row.text


def test_clean_internships_parsed_fields(raw_sample, vocab):
    out = clean_internships(raw_sample, vocab).set_index("source_id")
    assert out.loc["2025TEST0001", "application_deadline"] == date(2025, 10, 15)
    assert out.loc["2025TEST0006", "application_deadline"] is None
    assert out.loc["2025TEST0002", "work_mode"] == "Remote"
    assert out.loc["2025TEST0007", "specialization"] == "CSE"
    assert "Mumbai" in out.loc["2025TEST0008", "eligibility_criteria"]
    assert out.loc["2025TEST0006", "stipend_min"] == 0


# --- job-role data -------------------------------------------------------------------------
def test_clean_internships_drops_identical_listings(raw_sample, vocab):
    """Same title + company + location + stipend + skills -> one listing (first kept); count recorded."""
    base = clean_internships(raw_sample, vocab)
    assert base.attrs["duplicates_removed"] == 0
    dupes = pd.DataFrame([_row(101), _row(102, apply_by="20 Oct' 25"), _row(103, location="Pune")], columns=COLS)
    df = clean_internships(pd.concat([raw_sample, dupes], ignore_index=True), vocab)
    assert df.attrs["duplicates_removed"] == 2                          # 101 and 102 repeat row 1
    assert len(df) == len(base) + 1
    ids = set(df["source_id"])
    assert "2025TEST0001" in ids and not {"2025TEST0101", "2025TEST0102"} & ids
    assert "2025TEST0103" in ids                                        # different location: kept
    key = ["internship_title", "company_name", "location", "stipend_text", "required_skills_text"]
    assert not df.duplicated(subset=key).any()


def test_clean_internships_start_date_is_its_own_field(raw_sample, vocab):
    df = clean_internships(raw_sample, vocab).set_index("source_id")
    assert df.loc["2025TEST0001", "start_date"] == "Immediately"
    assert "Start:" not in " ".join(df["eligibility_criteria"].astype(str))


def test_job_role_dedup_before_split(vocab):
    df = pd.DataFrame({"Career": ["Data Science", "Data Science"], "Skill": ["Python", "Python"]})
    assert len(clean_job_role_data(df, vocab)) == 1


def test_job_role_dedup_after_normalisation(vocab):
    df = pd.DataFrame({"Career": ["Data Science", "Data Science"], "Skill": ["Python, SQL", "sql, py"]})
    out = clean_job_role_data(df, vocab)
    assert len(out) == 1 and out.iloc[0].skills == ["python", "sql"]


def test_job_role_drops_rows_without_known_skills(vocab):
    df = pd.DataFrame({"Career": ["Security", "Data Science"], "Skill": ["Underwater welding", "Python"]})
    out = clean_job_role_data(df, vocab)
    assert list(out.career) == ["Data Science"]
