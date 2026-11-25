"""Assessments, MCQs, attempts and answers (spec §10; rules 9, 10, 12)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum

from ml_core.eligibility import REQUIRED_QUALIFICATIONS, SPECIALIZATIONS

OPTIONS = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]


class Assessment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    assessment_name = models.CharField(max_length=200)
    qualification = models.CharField(max_length=30, choices=[(q, q) for q in REQUIRED_QUALIFICATIONS],
                                      help_text="Students whose qualification satisfies this can take it.")
    specialization = models.CharField(max_length=30, blank=True, default="",
                                      choices=[(s, s) for s in SPECIALIZATIONS])
    duration_minutes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.INACTIVE, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["assessment_name"]

    def __str__(self) -> str:
        return self.assessment_name

    def total_marks(self) -> Decimal:
        return self.questions.aggregate(t=Sum("marks"))["t"] or Decimal("0")


class Question(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    option_a = models.CharField(max_length=300)
    option_b = models.CharField(max_length=300)
    option_c = models.CharField(max_length=300)
    option_d = models.CharField(max_length=300)
    correct_option = models.CharField(max_length=1, choices=OPTIONS)
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1"),
                                validators=[MinValueValidator(Decimal("0"))])

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.question_text[:60]


class Attempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        SUBMITTED = "SUBMITTED", "Submitted"
        AUTO_SUBMITTED = "AUTO_SUBMITTED", "Auto-submitted"

    class Result(models.TextChoices):
        QUALIFIED = "QUALIFIED", "Qualified"
        NOT_QUALIFIED = "NOT_QUALIFIED", "Not qualified"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="attempts")
    assessment = models.ForeignKey(Assessment, on_delete=models.PROTECT, related_name="attempts")
    start_time = models.DateTimeField()
    deadline = models.DateTimeField()
    submission_time = models.DateTimeField(null=True, blank=True)
    total_marks = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    obtained_marks = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    #: unrounded enough for the >60 rule; displayed with 2 decimals
    score_percentage = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    result = models.CharField(max_length=15, choices=Result.choices, null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)

    class Meta:
        ordering = ["-start_time"]
        constraints = [models.UniqueConstraint(fields=["student", "assessment"], condition=Q(status="IN_PROGRESS"),
                                               name="one_in_progress_attempt")]
        indexes = [models.Index(fields=["student", "status"])]

    def __str__(self) -> str:
        return f"{self.student} – {self.assessment} ({self.status})"

    @property
    def is_finished(self) -> bool:
        return self.status != self.Status.IN_PROGRESS


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="answers")
    selected_option = models.CharField(max_length=1, choices=OPTIONS, null=True, blank=True)
    correct_option = models.CharField(max_length=1, choices=OPTIONS, blank=True, default="")
    is_correct = models.BooleanField(default=False)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="one_answer_per_question")]
