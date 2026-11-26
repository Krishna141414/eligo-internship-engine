from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.models import User
from adminpanel import services
from assessments.models import Assessment, Attempt
from assessments.services import FINISHED
from recommendations.models import InternshipRecommendation, JobRolePrediction
from recommendations.services import ai_status
from students.models import StudentProfile


@admin_required
def dashboard(request):
    counts = services.dashboard_counts()
    recent = Attempt.objects.filter(status__in=FINISHED).select_related("student", "assessment").order_by("-submission_time")[:8]
    per_internship = services.recommendations_per_internship()
    return render(request, "adminpanel/dashboard.html", {
        "c": counts, "recent_attempts": recent, "outcomes": services.student_outcomes(counts),
        "recs_chart": services.recommendations_chart(per_internship, counts["recommendation_runs"]),
        "recs_rows": per_internship, "min_runs": services.MIN_RUNS_FOR_CHART})


@admin_required
def students(request):
    qs = services.students().select_related("profile").order_by("-registered_date")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
    if status in User.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "adminpanel/students.html", {"page": page, "q": q, "status": status})


@admin_required
def student_detail(request, pk):
    student = get_object_or_404(User, pk=pk, user_type=User.UserType.STUDENT)
    profile = StudentProfile.objects.filter(student=student).first()
    attempts = Attempt.objects.filter(student=student).select_related("assessment")
    latest = InternshipRecommendation.objects.filter(student=student).order_by("-generated_date").first()
    recs = (InternshipRecommendation.objects.filter(student=student, run_id=latest.run_id)
            .select_related("internship").order_by("recommendation_rank") if latest else [])
    return render(request, "adminpanel/student_detail.html", {
        "s": student, "profile": profile, "attempts": attempts, "recs": recs,
        "predictions": JobRolePrediction.objects.filter(student=student)[:5]})


@admin_required
@require_POST
def student_toggle(request, pk):
    student = get_object_or_404(User, pk=pk, user_type=User.UserType.STUDENT)
    student.status = User.Status.INACTIVE if student.status == User.Status.ACTIVE else User.Status.ACTIVE
    student.save(update_fields=["status", "is_active"])
    messages.success(request, f"{student.name} is now {student.get_status_display().lower()}.")
    return redirect(request.POST.get("next") or "adminpanel:students")


@admin_required
def results(request):
    qs = Attempt.objects.filter(status__in=FINISHED).select_related("student", "assessment").order_by("-submission_time")
    assessment = request.GET.get("assessment", "")
    result = request.GET.get("result", "")
    if assessment.isdigit():
        qs = qs.filter(assessment_id=int(assessment))
    if result in Attempt.Result.values:
        qs = qs.filter(result=result)
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "adminpanel/results.html", {
        "page": page, "assessments": Assessment.objects.all(), "assessment": assessment, "result": result})


@admin_required
def recommendations(request):
    runs = (InternshipRecommendation.objects.values("run_id", "student_id", "student__name", "student__email")
            .annotate(generated=Max("generated_date"), n=Count("id"), top=Max("final_match_score"))
            .order_by("-generated"))
    page = Paginator(runs, 25).get_page(request.GET.get("page"))
    rows = {r.run_id: r for r in InternshipRecommendation.objects.filter(
        run_id__in=[p["run_id"] for p in page.object_list], recommendation_rank=1).select_related("internship")}
    for p in page.object_list:
        p["first"] = rows.get(p["run_id"])
    return render(request, "adminpanel/recommendations.html", {"page": page})


@admin_required
def recommendation_run(request, run_id):
    rows = list(InternshipRecommendation.objects.filter(run_id=run_id).select_related("internship", "student")
                .order_by("recommendation_rank"))
    if not rows:
        raise Http404
    return render(request, "adminpanel/recommendation_run.html", {"rows": rows, "student": rows[0].student})


@admin_required
def recommendation_detail(request, pk):
    rec = get_object_or_404(InternshipRecommendation.objects.select_related("internship", "student"), pk=pk)
    return render(request, "adminpanel/recommendation_detail.html", {"rec": rec, "x": rec.explanation})


@admin_required
def ml(request):
    metrics = services.read_metrics()
    manifest = services.read_manifest()
    return render(request, "adminpanel/ml.html", {
        "metrics": metrics, "manifest": manifest, "figures": services.figure_entries(), "status": ai_status(),
        "ml_chart": services.model_comparison(metrics),
        "predictions": JobRolePrediction.objects.select_related("student")[:50]})


@admin_required
def figure(request, name):
    path = services.figure_path(name)
    if path is None:
        raise Http404
    return FileResponse(open(path, "rb"), content_type="image/png")
