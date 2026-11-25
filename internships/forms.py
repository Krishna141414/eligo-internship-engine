from django import forms

from internships.models import Internship
from internships.services import parse_skills_input, skill_vocab
from ml_core.preprocessing import parse_duration_months, parse_stipend

SPEC_REQUIRED = ("company_name", "job_role", "required_qualification", "location", "stipend", "duration",
                 "eligibility_criteria", "application_deadline")


class InternshipForm(forms.ModelForm):
    """Admin add/edit form with every spec §11.4 field. Skills are normalised to the canonical vocabulary."""

    required_skills = forms.CharField(
        label="Required skills", help_text="Comma-separated, e.g. Python, SQL, Excel.",
        widget=forms.TextInput(attrs={"autocomplete": "off"}))

    class Meta:
        model = Internship
        fields = ["company_name", "internship_title", "job_role", "description", "required_qualification",
                  "specialization", "minimum_academic_percentage", "required_skills", "location", "work_mode",
                  "stipend", "duration", "eligibility_criteria", "application_deadline", "status"]
        widgets = {"application_deadline": forms.DateInput(attrs={"type": "date"}),
                   "description": forms.Textarea(attrs={"rows": 4}),
                   "eligibility_criteria": forms.Textarea(attrs={"rows": 3})}
        labels = {"minimum_academic_percentage": "Minimum academic percentage",
                  "stipend": "Stipend (e.g. ₹ 10,000 /month or Unpaid)", "duration": "Duration (e.g. 3 Months)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in SPEC_REQUIRED:
            self.fields[name].required = True
        if self.instance.pk:
            self.initial["required_skills"] = ", ".join(self.instance.required_skills or [])

    def clean_required_skills(self):
        skills, unknown = parse_skills_input(self.cleaned_data["required_skills"], skill_vocab())
        if unknown:
            parts = []
            for token, suggestions in unknown.items():
                hint = f" (did you mean {', '.join(suggestions)}?)" if suggestions else ""
                parts.append(f"“{token}”{hint}")
            raise forms.ValidationError("These skills aren't in Eligo's skill list: " + "; ".join(parts)
                                        + ". Use the closest listed skill.")
        if not skills:
            raise forms.ValidationError("Add at least one required skill.")
        return skills

    def save(self, commit=True):
        obj = super().save(commit=False)
        stipend = parse_stipend(obj.stipend)
        obj.stipend_min, obj.stipend_max = stipend.min_inr, stipend.max_inr
        obj.duration_months = parse_duration_months(obj.duration)
        obj.description_derived = False
        if commit:
            obj.save()
        return obj


class InternshipSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Keyword")
    qualification = forms.ChoiceField(required=False, label="Qualification")
    job_role = forms.CharField(required=False, label="Job role")
    location = forms.CharField(required=False, label="Location")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ml_core.eligibility import QUALIFICATIONS
        self.fields["qualification"].choices = [("", "Any")] + [(q, q) for q in QUALIFICATIONS]
