"""DEMO / illustrative student profiles (hard rule 7).

These are hand-written profiles for demonstrating the engine in the notebook and in the web app
(`python manage.py seed_demo`). They are NOT training data and every label starts with "DEMO".
One shared definition keeps the notebook and Django demos identical (hard rule 5).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DemoProfile:
    label: str
    qualification: str
    specialization: str
    college_name: str
    academic_percentage: Decimal
    skills: str                      # free text, used for internship matching
    career_skills: tuple[str, ...]   # from the job-role model's vocabulary (D-022), used for prediction
    interests: str
    preferred_role: str
    preferred_location: str
    assessment_score: Decimal        # DEMO score used in the notebook; Django students take real assessments
    expected_career: str | None      # what a reasonable person would expect; None = outside model scope


DEMO_PROFILES: dict[str, DemoProfile] = {
    "cs": DemoProfile(
        label="DEMO – B.Tech CSE (Python/ML)", qualification="B.Tech", specialization="CSE",
        college_name="DEMO Institute of Technology", academic_percentage=Decimal("78"),
        skills="Python, Machine Learning, SQL, Data Analysis, Deep Learning",
        career_skills=("artificial intelligence", "deep learning", "machine learning", "neural networks",
                       "research on artificial intelligence and machine learning"),
        interests="AI and machine learning", preferred_role="Machine Learning Engineer",
        preferred_location="Bangalore", assessment_score=Decimal("72.5"), expected_career="Artificial Intelligence"),
    "bba": DemoProfile(
        label="DEMO – BBA (marketing)", qualification="BBA", specialization="Management",
        college_name="DEMO College of Commerce", academic_percentage=Decimal("68"),
        skills="Digital Marketing, Social Media Marketing, Content Writing, Canva",
        career_skills=("digital marketing", "social media management"),
        interests="brand marketing", preferred_role="Marketing Executive", preferred_location="Mumbai",
        assessment_score=Decimal("66"), expected_career=None),
    "bsc": DemoProfile(
        label="DEMO – B.Sc (scored 55%)", qualification="B.Sc", specialization="Science",
        college_name="DEMO Science College", academic_percentage=Decimal("70"),
        skills="MS-Excel, Data Entry, Statistics",
        career_skills=("data analysis", "statistics"),
        interests="operations and analytics", preferred_role="Analyst", preferred_location="Delhi",
        assessment_score=Decimal("55"), expected_career="Data Science"),
}
