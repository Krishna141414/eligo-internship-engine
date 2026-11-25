from django import forms

from accounts.models import User
from internships.services import parse_skills_input, skill_vocab
from ml_core.job_role import suggest_career_skills
from students.models import StudentProfile
from students.services import career_skill_vocab

CAREER_SKILLS_LABEL = "Skills the job-role model understands"
CAREER_SKILLS_HELP = ("Pick the skills from this list that describe you (at least 3). The job-role prediction "
                      "uses only these. Your free-text skills above are used for internship matching.")


class StudentProfileForm(forms.ModelForm):
    skills = forms.CharField(label="Your skills", help_text="Comma-separated, e.g. Python, SQL, Excel. Used for internship matching.",
                             widget=forms.TextInput(attrs={"autocomplete": "off", "data-tag-input": "skill-suggestions"}))
    career_skills = forms.MultipleChoiceField(label=CAREER_SKILLS_LABEL, help_text=CAREER_SKILLS_HELP, required=False,
                                              widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = StudentProfile
        fields = ["qualification", "specialization", "college_name", "academic_percentage", "skills",
                  "career_skills", "career_interests", "preferred_job_role", "preferred_location"]
        labels = {"academic_percentage": "Academic percentage", "college_name": "College name",
                  "preferred_job_role": "Preferred job role", "preferred_location": "Preferred location",
                  "career_interests": "Career interests"}
        widgets = {"career_interests": forms.Textarea(attrs={"rows": 2})}
        error_messages = {
            "qualification": {"required": "Your profile is missing qualification. Add it to see matches."},
            "academic_percentage": {"required": "Your profile is missing academic percentage. Add it to see matches.",
                                    "max_value": "Academic percentage can't be more than 100.",
                                    "min_value": "Academic percentage can't be negative."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["qualification"].required = True
        self.fields["academic_percentage"].required = True
        vocab = career_skill_vocab()
        self.fields["career_skills"].choices = [(s, s) for s in vocab]
        self.suggested_career_skills: list[str] = []
        if self.instance.pk:
            self.initial["skills"] = ", ".join(self.instance.skills or [])
            if self.instance.career_skills:
                self.initial["career_skills"] = list(self.instance.career_skills)
            else:
                self.suggested_career_skills = suggest_career_skills(self.instance.skills or [], vocab)
                self.initial["career_skills"] = list(self.suggested_career_skills)

    def clean_skills(self):
        skills, unknown = parse_skills_input(self.cleaned_data["skills"], skill_vocab())
        if unknown:
            parts = [f"“{t}”" + (f" (did you mean {', '.join(s)}?)" if s else "") for t, s in unknown.items()]
            raise forms.ValidationError("These skills aren't in Eligo's skill list: " + "; ".join(parts)
                                        + ". Use the closest listed skill.")
        if not skills:
            raise forms.ValidationError("Your profile is missing skills. Add at least one to see matches.")
        return skills

    def clean_career_skills(self):
        return sorted(set(self.cleaned_data.get("career_skills") or []))


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "mobile_number"]
        labels = {"name": "Full name", "mobile_number": "Mobile number"}
