from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from accounts.models import User

INACTIVE_MESSAGE = "Your account is inactive. Contact the admin."


class EmailAuthenticationForm(AuthenticationForm):
    """Login by email. Inactive users get a clear message instead of the generic error."""

    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email",
                                                                         "spellcheck": "false"}))

    def clean(self):
        email = (self.cleaned_data.get("username") or "").lower()
        password = self.cleaned_data.get("password")
        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                candidate = User.objects.filter(email=email).first()
                if candidate and not candidate.is_active and candidate.check_password(password):
                    raise forms.ValidationError(INACTIVE_MESSAGE, code="inactive")
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class StudentRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("name", "email", "mobile_number")
        labels = {"name": "Full name", "mobile_number": "Mobile number"}
        help_texts = {"mobile_number": "10-digit Indian mobile number."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mobile_number"].required = True
        for name, token in (("name", "name"), ("email", "email"), ("mobile_number", "tel")):
            self.fields[name].widget.attrs["autocomplete"] = token
        self.fields["mobile_number"].widget.attrs["inputmode"] = "numeric"
        self.fields["email"].widget.attrs["spellcheck"] = "false"

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists. Log in instead.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = User.UserType.STUDENT
        if commit:
            user.save()
        return user
