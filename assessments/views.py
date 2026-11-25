from django.contrib import messages
from django.db.models import Count, ProtectedError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, student_required
from assessments import services
from assessments.forms import AssessmentForm, QuestionForm
from assessments.models import Assessment, Attempt, Question
from ml_core.config import PASS_THRESHOLD
from students.services import get_profile


def _own_attempt(request, pk) -> Attempt:
    """404 (not 403) for anyone else's attempt (spec §16)."""
    return get_object_or_404(Attempt.objects.select_related("assessment"), pk=pk, student=request.user)


# --- student ----------------------------------------------------------------------------------------
@student_required
def assessment_list(request):
    services.finalise_expired_for(request.user)
    profile = get_profile(request.user)
    qualification = profile.qualification if profile else ""
    return render(request, "assessments/list.html", {
        "assessments": services.available_assessments(qualification),
        "has_qualification": bool(qualification),
        "in_progress": {a.assessment_id: a for a in Attempt.objects.filter(student=request.user, status=Attempt.Status.IN_PROGRESS)},
        "history": Attempt.objects.filter(student=request.user, status__in=services.FINISHED).select_related("assessment"),
    })


@student_required
@require_POST
def start(request, pk):
    profile = get_profile(request.user)
    assessment = get_object_or_404(services.available_assessments(profile.qualification if profile else ""), pk=pk)
    attempt = services.start_or_resume(request.user, assessment, timezone.now())
    return redirect("assessments:exam", attempt.pk)


@student_required
def exam(request, pk):
    attempt = _own_attempt(request, pk)
    now = timezone.now()
    services.finalise_if_expired(attempt, now)
    attempt.refresh_from_db()
    if attempt.is_finished:
        return redirect("assessments:result", attempt.pk)
    questions = services.exam_questions(attempt)
    return render(request, "assessments/exam.html", {
        "attempt": attempt, "questions": questions, "remaining_seconds": services.remaining_seconds(attempt, now),
        "answered": sum(1 for q in questions if q["selected"]),
    })


@student_required
@require_POST
def save_answer(request, pk):
    attempt = _own_attempt(request, pk)
    try:
        saved = services.save_answer(attempt, request.POST.get("question"), request.POST.get("option"), timezone.now())
    except services.AnswerError as exc:
        return JsonResponse({"saved": False, "error": str(exc)}, status=400)
    if not saved:
        return JsonResponse({"saved": False, "error": "Time is up. Your answers saved so far will be graded."}, status=409)
    return JsonResponse({"saved": True})


@student_required
@require_POST
def submit(request, pk):
    attempt = _own_attempt(request, pk)
    posted = {key[2:]: value for key, value in request.POST.items() if key.startswith("q_")}
    try:
        outcome = services.submit(attempt.pk, request.user, posted, timezone.now())
    except services.AnswerError as exc:
        messages.error(request, f"{exc} Please check your answers and submit again.")
        return redirect("assessments:exam", attempt.pk)
    if outcome.status == "duplicate":
        messages.info(request, "This assessment was already submitted. Here is your result.")
    elif outcome.status == "auto_submitted":
        messages.warning(request, "Time was up, so your assessment was submitted automatically with the answers saved before the deadline.")
    else:
        messages.success(request, "Assessment submitted.")
    return redirect("assessments:result", attempt.pk)


@student_required
def result(request, pk):
    attempt = _own_attempt(request, pk)
    if not attempt.is_finished:
        raise Http404
    answers = attempt.answers.all()
    return render(request, "assessments/result.html", {
        "attempt": attempt, "total_questions": answers.count(), "correct": answers.filter(is_correct=True).count(),
        "threshold": PASS_THRESHOLD,
    })


# --- admin --------------------------------------------------------------------------------------------
@admin_required
def admin_list(request):
    return render(request, "assessments/admin_list.html", {
        "assessments": Assessment.objects.annotate(n_questions=Count("questions"), n_attempts=Count("attempts", distinct=True))})


@admin_required
def admin_add(request):
    form = AssessmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"Assessment “{obj}” created. Add questions, then activate it.")
        return redirect("assessments:questions", obj.pk)
    return render(request, "assessments/admin_form.html", {"form": form, "title": "Create assessment"})


@admin_required
def admin_edit(request, pk):
    obj = get_object_or_404(Assessment, pk=pk)
    form = AssessmentForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Assessment updated.")
        return redirect("assessments:admin_list")
    return render(request, "assessments/admin_form.html", {"form": form, "title": "Edit assessment", "obj": obj})


@admin_required
@require_POST
def admin_toggle(request, pk):
    obj = get_object_or_404(Assessment, pk=pk)
    if obj.status == Assessment.Status.ACTIVE:
        obj.status = Assessment.Status.INACTIVE
        messages.success(request, f"“{obj}” deactivated. Past attempts are kept.")
    else:
        ok, reason = services.can_activate(obj)
        if not ok:
            messages.error(request, reason)
            return redirect("assessments:questions", obj.pk)
        obj.status = Assessment.Status.ACTIVE
        messages.success(request, f"“{obj}” is now active.")
    obj.save(update_fields=["status"])
    return redirect("assessments:admin_list")


@admin_required
def questions(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    return render(request, "assessments/questions.html",
                  {"assessment": assessment, "questions": assessment.questions.annotate(n_answers=Count("answers"))})


@admin_required
def question_add(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        q = form.save(commit=False)
        q.assessment = assessment
        q.save()
        messages.success(request, "Question added.")
        return redirect("assessments:questions", assessment.pk)
    return render(request, "assessments/question_form.html", {"form": form, "assessment": assessment, "title": "Add question"})


@admin_required
def question_edit(request, pk):
    q = get_object_or_404(Question.objects.select_related("assessment"), pk=pk)
    form = QuestionForm(request.POST or None, instance=q)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Question updated.")
        return redirect("assessments:questions", q.assessment_id)
    return render(request, "assessments/question_form.html", {"form": form, "assessment": q.assessment, "title": "Edit question"})


@admin_required
@require_POST
def question_delete(request, pk):
    q = get_object_or_404(Question, pk=pk)
    assessment_id = q.assessment_id
    try:
        q.delete()
        messages.success(request, "Question deleted.")
    except ProtectedError:
        messages.error(request, "This question has student answers and can't be deleted. Deactivate the assessment instead.")
    return redirect("assessments:questions", assessment_id)
