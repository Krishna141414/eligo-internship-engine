"""Internship listings (spec §10 "Internships"; D-007 derived fields; D-014 embedding cache)."""
import hashlib

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from ml_core.eligibility import REQUIRED_QUALIFICATIONS, SPECIALIZATIONS
from ml_core.preprocessing import build_internship_text


class InternshipQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=Internship.Status.ACTIVE)


class Internship(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    class WorkMode(models.TextChoices):
        REMOTE = "Remote", "Remote"
        ONSITE = "On-site", "On-site"
        HYBRID = "Hybrid", "Hybrid"

    source_id = models.CharField(max_length=40, unique=True, null=True, blank=True,
                                 help_text="Row id in the public dataset; empty for admin-added internships.")
    company_name = models.CharField(max_length=200)
    internship_title = models.CharField(max_length=200)
    job_role = models.CharField(max_length=200)
    description = models.TextField()
    description_derived = models.BooleanField(default=False)
    required_qualification = models.CharField(max_length=30, default="Any Graduate",
                                              choices=[(q, q) for q in REQUIRED_QUALIFICATIONS])
    specialization = models.CharField(max_length=30, blank=True, default="",
                                      choices=[(s, s) for s in SPECIALIZATIONS])
    minimum_academic_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                                      validators=[MinValueValidator(0), MaxValueValidator(100)])
    required_skills = models.JSONField(default=list, blank=True)
    location = models.CharField(max_length=200)
    work_mode = models.CharField(max_length=10, choices=WorkMode.choices, default=WorkMode.ONSITE)
    stipend = models.CharField(max_length=100, blank=True, default="")
    stipend_min = models.PositiveIntegerField(null=True, blank=True)
    stipend_max = models.PositiveIntegerField(null=True, blank=True)
    duration = models.CharField(max_length=50, blank=True, default="")
    duration_months = models.FloatField(null=True, blank=True)
    eligibility_criteria = models.TextField(blank=True, default="")
    application_deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    derived_fields = models.JSONField(default=list, blank=True)
    # D-014 embedding cache: imported rows point into internships.npy; edited/new rows store their own
    embedding = models.JSONField(null=True, blank=True)
    embedding_row = models.PositiveIntegerField(null=True, blank=True)
    embedding_text_hash = models.CharField(max_length=64, blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = InternshipQuerySet.as_manager()

    class Meta:
        ordering = ["-created", "id"]
        indexes = [models.Index(fields=["status", "location"]), models.Index(fields=["required_qualification"])]

    def __str__(self) -> str:
        return f"{self.internship_title} @ {self.company_name}"

    def text_for_matching(self) -> str:
        """Exactly the text the notebook embedded (title, role, skills, description)."""
        return build_internship_text(self.internship_title, self.job_role, self.required_skills, "", "",
                                     self.description)

    def text_hash(self) -> str:
        return hashlib.sha256(self.text_for_matching().encode("utf-8")).hexdigest()
