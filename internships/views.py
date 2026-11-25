from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, student_required
from assessments.services import score_for_gates
from internships.forms import InternshipForm, InternshipSearchForm
from internships.models import Internship
from internships.services import gate_date, internship_facts, requirements_open_to
from ml_core.eligibility import evaluate_gates
from students.services import get_profile, student_facts


# --- student --------------------------------------------------------------------------------------
@student_required
def internship_list(request):
    form = InternshipSearchForm(request.GET or None)
    qs = Internship.objects.active()
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            qs = qs.filter(Q(internship_title__icontains=d["q"]) | Q(company_name__icontains=d["q"])
                           | Q(required_skills__icontains=d["q"].lower()))
        if d["qualification"]:
            qs = qs.filter(required_qualification__in=requirements_open_to(d["qualification"]))
        if d["job_role"]:
            qs = qs.filter(Q(job_role__icontains=d["job_role"]) | Q(internship_title__icontains=d["job_role"]))
        if d["location"]:
            qs = qs.filter(location__icontains=d["location"])
    page = Paginator(qs.order_by("internship_title", "pk"), 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "internships/list.html", {"form": form, "page": page, "total": qs.count(),
                                                     "querystring": params.urlencode()})


@student_required
def internship_detail(request, pk):
    internship = get_object_or_404(Internship.objects.active(), pk=pk)
    profile = get_profile(request.user)
    missing = profile.missing_fields() if profile else ["qualification", "academic percentage", "skills"]
    gates = None
    if not missing:
        score, _ = score_for_gates(request.user, profile.qualification)
        gates = evaluate_gates(student_facts(profile), internship_facts(internship), score, gate_date(internship))
    return render(request, "internships/detail.html",
                  {"internship": internship, "gates": gates, "missing": missing})


# --- admin ------------------------------------------------------------------------------------------
@admin_required
def admin_list(request):
    qs = Internship.objects.all()
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        qs = qs.filter(Q(internship_title__icontains=q) | Q(company_name__icontains=q) | Q(location__icontains=q))
    if status in Internship.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs.order_by("-created", "pk"), 25).get_page(request.GET.get("page"))
    return render(request, "internships/admin_list.html", {"page": page, "q": q, "status": status,
                                                           "total": qs.count()})


@admin_required
def admin_add(request):
    form = InternshipForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"Internship “{obj}” added.")
        return redirect("internships:admin_list")
    return render(request, "internships/admin_form.html", {"form": form, "title": "Add internship"})


@admin_required
def admin_edit(request, pk):
    obj = get_object_or_404(Internship, pk=pk)
    form = InternshipForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Internship “{obj}” updated.")
        return redirect("internships:admin_list")
    return render(request, "internships/admin_form.html", {"form": form, "title": "Edit internship", "obj": obj})


@admin_required
@require_POST
def admin_toggle(request, pk):
    obj = get_object_or_404(Internship, pk=pk)
    obj.status = Internship.Status.INACTIVE if obj.status == Internship.Status.ACTIVE else Internship.Status.ACTIVE
    obj.save(update_fields=["status", "updated"])
    messages.success(request, f"“{obj}” is now {obj.get_status_display().lower()}.")
    return redirect(request.POST.get("next") or "internships:admin_list")
