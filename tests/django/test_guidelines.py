"""Phase 7: fixes from the Vercel Web Interface Guidelines audit (docs/AUDIT.md). Fixtures only."""
import re
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.messages import constants
from django.urls import reverse

from assessments.models import Assessment, Question
from students.models import StudentProfile

pytestmark = pytest.mark.django_db
ROOT = Path(settings.BASE_DIR)
CSS = (ROOT / "static" / "css" / "theme.css").read_text(encoding="utf-8")
UI_JS = (ROOT / "static" / "js" / "ui.js").read_text(encoding="utf-8")


def test_success_messages_are_polite_status_errors_are_alerts(student_client, student):
    StudentProfile.objects.create(student=student, qualification="B.Tech", academic_percentage=Decimal("70"), skills=["python"])
    html = student_client.post(reverse("students:account_edit"), {"name": "New Name (fixture)", "mobile_number": "9876543210"},
                               follow=True).content.decode()
    assert re.search(r'class="alert alert-success" role="status"', html)
    assert 'role="alert"' not in html


def test_email_inputs_skip_spellcheck(client):
    for name in ("accounts:login", "accounts:register"):
        html = client.get(reverse(name)).content.decode()
        email = re.search(r'<input[^>]*type="email"[^>]*>', html).group(0)
        assert 'spellcheck="false"' in email, name


def test_question_delete_asks_for_confirmation(admin_client_):
    a = Assessment.objects.create(assessment_name="Aptitude (fixture)", qualification="Any Graduate", duration_minutes=10)
    Question.objects.create(assessment=a, question_text="Q?", option_a="a", option_b="b", option_c="c", option_d="d",
                            correct_option="A")
    html = admin_client_.get(reverse("assessments:questions", args=[a.pk])).content.decode()
    assert re.search(r'<form[^>]*data-confirm="Delete this question\?[^"]*"', html)
    assert "data-confirm" in UI_JS and "window.confirm" in UI_JS


def test_invalid_fields_are_marked_and_the_first_one_gets_focus(client):
    html = client.post(reverse("accounts:register"), {"name": "", "email": "bad", "mobile_number": "1",
                                                      "password1": "x", "password2": "y"}).content.decode()
    assert re.search(r'<input[^>]*name="email"[^>]*aria-invalid="true"', html)
    assert "[aria-invalid=\"true\"]" in UI_JS and ".focus()" in UI_JS


def test_forms_warn_before_leaving_with_unsaved_changes(student_client, fake_artifacts):
    html = student_client.get(reverse("students:profile_edit")).content.decode()
    assert re.search(r"<form[^>]*data-warn-unsaved", html)
    assert "beforeunload" in UI_JS


def test_profile_fields_have_autocomplete_tokens(student_client, fake_artifacts):
    html = student_client.get(reverse("students:profile_edit")).content.decode()
    tokens = {m.group(2): m.group(1) for m in
              re.finditer(r'<(?:input|textarea|select)[^>]*?autocomplete="([\w-]+)"[^>]*?name="(\w+)"', html)}
    tokens.update({m.group(1): m.group(2) for m in
                   re.finditer(r'<(?:input|textarea|select)[^>]*?name="(\w+)"[^>]*?autocomplete="([\w-]+)"', html)})
    assert tokens.get("college_name") == "organization" and tokens.get("preferred_location") == "address-level2"
    assert tokens.get("career_interests") == "off" and tokens.get("academic_percentage") == "off"


def test_skill_filter_placeholder_shows_an_example(student_client, fake_artifacts):
    html = student_client.get(reverse("students:profile_edit")).content.decode()
    assert re.search(r'placeholder="[^"]*e\.g\. [^"]+…"', html)


def test_sticky_bars_never_cover_focus_or_anchors():
    assert re.search(r"html \{[^}]*scroll-padding-top", CSS)
    assert re.search(r"\.question \{[^}]*scroll-margin-top", CSS)


def test_touch_and_overscroll_behaviour():
    assert "touch-action: manipulation" in CSS and "-webkit-tap-highlight-color" in CSS
    assert re.search(r"\.app-sidebar[^{]*\{[^}]*overscroll-behavior: contain", CSS)
    assert re.search(r"\.modal[^{]*\{[^}]*overscroll-behavior: contain", CSS)


def test_long_content_wraps_and_selects_are_explicit():
    assert re.search(r"\.chip \{[^}]*overflow-wrap: anywhere", CSS)
    assert re.search(r"\.form-select \{[^}]*background-color: var\(--surface\)", CSS)
    assert re.search(r":root \{[^}]*color-scheme: light", CSS)


def test_head_preloads_fonts_sets_theme_colour_and_brand_is_not_translated(client):
    html = client.get(reverse("accounts:login")).content.decode()
    assert len(re.findall(r'<link rel="preload" href="[^"]+\.woff2" as="font" type="font/woff2" crossorigin>', html)) >= 2
    assert '<meta name="theme-color" content="#F6F8FB">' in html
    assert re.search(r'class="wordmark[^"]*"[^>]*translate="no"', html)


class _Text(HTMLParser):
    """Visible text only: skips script/style and anything inside {% %} / {{ }} template syntax."""
    def __init__(self):
        super().__init__()
        self.skip, self.chunks = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.chunks.append(re.sub(r"\{%.*?%\}|\{\{.*?\}\}|\{#.*?#\}", " ", data, flags=re.S))


def test_visible_copy_uses_curly_quotes():
    offenders = []
    for f in (ROOT / "templates").rglob("*.html"):
        p = _Text()
        p.feed(f.read_text(encoding="utf-8"))
        for chunk in p.chunks:
            if re.search(r"[A-Za-z]'[A-Za-z]|\"", chunk):
                offenders.append(f"{f.relative_to(ROOT)}: {chunk.strip()[:60]}")
    assert offenders == []
