from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import student_required
from recommendations import services
from recommendations.models import InternshipRecommendation, JobRolePrediction


@student_required
@require_http_methods(["GET", "POST"])
def recommendation_list(request):
    if request.method == "POST":
        run = services.generate_recommendations(request.user)
        if run.reason:
            messages.warning(request, run.reason)
        else:
            messages.success(request, f"Generated {len(run.eligible)} recommendations.")
        return redirect("recommendations:list")
    latest = InternshipRecommendation.objects.filter(student=request.user).order_by("-generated_date").first()
    rows = []
    if latest is not None:
        rows = list(InternshipRecommendation.objects.filter(student=request.user, run_id=latest.run_id)
                    .select_related("internship").order_by("recommendation_rank"))
    preview, n_failing = services.ineligible_preview_for(request.user)
    return render(request, "recommendations/list.html", {
        "rows": rows, "latest": latest, "preview": preview, "not_eligible_count": n_failing})


@student_required
def recommendation_detail(request, pk):
    rec = get_object_or_404(InternshipRecommendation.objects.select_related("internship", "assessment_attempt"),
                            pk=pk, student=request.user)
    return render(request, "recommendations/detail.html", {"rec": rec, "x": rec.explanation})


@student_required
@require_http_methods(["POST"])
def second_opinion(request, pk):
    """JSON: run (or return) the local-LLM cross-check for one of the student's own recommendations."""
    rec = get_object_or_404(InternshipRecommendation.objects.select_related("internship", "student"),
                            pk=pk, student=request.user)
    rec = services.run_second_opinion(rec)
    gap = rec.explanation.get("llm_gap") or {}
    return JsonResponse({"status": rec.second_opinion, "method": rec.analysis_method,
                         "matched": gap.get("matched", []), "missing": gap.get("missing", []),
                         "detail": rec.analysis_detail})


@student_required
@require_http_methods(["GET", "POST"])
def job_role(request):
    if request.method == "POST":
        pred, message = services.predict_job_role(request.user)
        if message:
            messages.warning(request, message)
        return redirect("recommendations:job_role")
    pred = JobRolePrediction.objects.filter(student=request.user).first()
    return render(request, "recommendations/job_role.html", {
        "pred": pred, "x": services.prediction_explanation(pred) if pred else None,
        "related": services.related_internships(pred, request.user) if pred else []})
