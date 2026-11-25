"""Student-side helpers: profile facts for the gates and the recommender."""
from __future__ import annotations

from decimal import Decimal

from ml_core.eligibility import StudentFacts
from ml_core.preprocessing import build_student_text
from students.models import StudentProfile


def get_profile(user) -> StudentProfile | None:
    return StudentProfile.objects.filter(student=user).first()


def student_facts(profile: StudentProfile) -> StudentFacts:
    skills = tuple(profile.skills or ())
    return StudentFacts(
        qualification=profile.qualification, specialization=profile.specialization,
        academic_percentage=Decimal(profile.academic_percentage or 0), skills=skills,
        text=build_student_text(skills, profile.career_interests, profile.preferred_job_role, profile.specialization))
