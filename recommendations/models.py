"""Stored AI results (spec §10 "Internship_Recommendations", "Job_Role_Predictions"; D-015, D-021)."""
import uuid

from django.conf import settings
from django.db import models


class InternshipRecommendation(models.Model):
    class Method(models.TextChoices):
        LLM = "llm", "LLM (local Ollama)"
        RULE_BASED = "rule_based", "Rule-based"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recommendations")
    internship = models.ForeignKey("internships.Internship", on_delete=models.PROTECT, related_name="recommendations")
    assessment_attempt = models.ForeignKey("assessments.Attempt", on_delete=models.PROTECT,
                                           related_name="recommendations")
    run_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    qualification_match = models.BooleanField(default=True)
    skill_match_score = models.FloatField()
    content_similarity_score = models.FloatField()
    semantic_similarity_score = models.FloatField()
    final_match_score = models.FloatField()
    recommendation_rank = models.PositiveSmallIntegerField()
    matched_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    recommendation_reason = models.TextField()
    explanation = models.JSONField(default=dict)
    analysis_method = models.CharField(max_length=12, choices=Method.choices, default=Method.RULE_BASED)
    analysis_detail = models.CharField(max_length=300, blank=True, default="")
    generated_date = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-generated_date", "recommendation_rank"]
        indexes = [models.Index(fields=["student", "run_id"])]

    def __str__(self) -> str:
        return f"#{self.recommendation_rank} {self.internship} for {self.student}"


class JobRolePrediction(models.Model):
    class Scope(models.TextChoices):
        CONFIDENT = "confident", "Confident"
        LOW_CONFIDENCE = "low_confidence", "Low confidence"
        OUT_OF_SCOPE = "out_of_scope", "Outside the model's scope"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="predictions")
    assessment_attempt = models.ForeignKey("assessments.Attempt", on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name="predictions")
    predicted_job_role = models.CharField(max_length=120, null=True, blank=True)
    probability = models.FloatField(null=True, blank=True)
    probabilities = models.JSONField(default=dict)
    scope_status = models.CharField(max_length=15, choices=Scope.choices)
    known_skills = models.JSONField(default=list)
    unknown_skills = models.JSONField(default=list)
    model_name = models.CharField(max_length=80)
    model_version = models.CharField(max_length=20)
    top_features = models.JSONField(default=list)
    predicted_date = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-predicted_date"]

    def __str__(self) -> str:
        return f"{self.predicted_job_role or 'no prediction'} for {self.student}"
