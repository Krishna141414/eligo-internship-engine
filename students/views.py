from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.decorators import student_required
from students.forms import AccountForm, StudentProfileForm
from internships.services import skill_vocab
from students.services import dashboard_context, get_profile


@student_required
def dashboard(request):
    return render(request, "students/dashboard.html", dashboard_context(request.user))


@student_required
def profile_edit(request):
    profile = get_profile(request.user)
    form = StudentProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.student = request.user
        obj.save()
        messages.success(request, "Profile saved.")
        return redirect("students:dashboard")
    vocab = skill_vocab()
    return render(request, "students/profile_form.html", {
        "form": form, "suggested_career_skills": form.suggested_career_skills,
        # Suggestions for the free-text skill box: the canonical vocabulary, minus one-letter tokens.
        "skill_suggestions": sorted(s for s in vocab.canonical if len(s) > 1) if vocab else []})


@student_required
def account_edit(request):
    form = AccountForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account details saved.")
        return redirect("students:dashboard")
    return render(request, "students/account_form.html", {"form": form})
