from django import forms

from assessments.models import Assessment, Question


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ["assessment_name", "qualification", "specialization", "duration_minutes"]
        labels = {"assessment_name": "Assessment name", "duration_minutes": "Duration (minutes)",
                  "qualification": "For students with qualification"}
        help_texts = {"qualification": "Students whose qualification satisfies this can take the assessment."}


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_option", "marks"]
        labels = {"option_a": "Option A", "option_b": "Option B", "option_c": "Option C", "option_d": "Option D",
                  "correct_option": "Correct answer"}
        widgets = {"question_text": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        data = super().clean()
        options = [data.get(f"option_{k}", "").strip().lower() for k in "abcd"]
        if all(options) and len(set(options)) < 4:
            raise forms.ValidationError("The four options must be different.")
        return data
