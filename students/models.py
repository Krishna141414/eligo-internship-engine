"""Student academic profile (spec §10 "Student_Profiles", §12.2; D-022 career skills)."""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from ml_core.eligibility import QUALIFICATIONS, SPECIALIZATIONS

PERCENT = [MinValueValidator(0), MaxValueValidator(100)]


class StudentProfile(models.Model):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    qualification = models.CharField(max_length=20, blank=True, default="",
                                      choices=[(q, q) for q in QUALIFICATIONS])
    specialization = models.CharField(max_length=30, blank=True, default="",
                                      choices=[(s, s) for s in SPECIALIZATIONS])
    college_name = models.CharField(max_length=200, blank=True, default="")
    academic_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                              validators=PERCENT)
    #: free-text skills, canonicalised; used for internship matching
    skills = models.JSONField(default=list, blank=True)
    #: chosen from the job-role model's own vocabulary (feature_schema.json); used ONLY for prediction (D-022)
    career_skills = models.JSONField(default=list, blank=True)
    career_interests = models.TextField(blank=True, default="")
    preferred_job_role = models.CharField(max_length=120, blank=True, default="")
    preferred_location = models.CharField(max_length=120, blank=True, default="")
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile of {self.student}"

    REQUIRED_FOR_MATCHING = ("qualification", "academic_percentage", "skills")

    def missing_fields(self) -> list[str]:
        """Fields a student must fill before eligibility and matching can run."""
        missing = []
        if not self.qualification:
            missing.append("qualification")
        if self.academic_percentage is None:
            missing.append("academic percentage")
        if not self.skills:
            missing.append("skills")
        return missing
