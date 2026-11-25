"""UI shell (spec §15, rules 16 and 19, D-023): every page has the title suffix, the disclaimer, the
wordmark and the vendored assets; templates never load anything from the internet; admin pages use
the sidebar shell and student pages the top bar."""
import re
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from assessments.models import Assessment
from internships.models import Internship
from students.models import StudentProfile

pytestmark = pytest.mark.django_db
DISCLAIMER = "Independent academic prototype, not affiliated with the official PM Internship Scheme portal."

STUDENT_PAGES = ["students:dashboard", "students:profile_edit", "students:account_edit", "internships:list",
                 "assessments:list", "recommendations:list", "recommendations:job_role", "accounts:password_change"]
ADMIN_PAGES = ["adminpanel:dashboard", "adminpanel:students", "adminpanel:results", "adminpanel:recommendations",
               "adminpanel:ml", "internships:admin_list", "internships:admin_add", "assessments:admin_list",
               "assessments:admin_add"]
PUBLIC_PAGES = ["accounts:login", "accounts:register"]


def _check_shell(html):
    assert re.search(r"<title>[^<]+ · Eligo</title>", html), "title suffix"
    assert DISCLAIMER in html
    assert "vendor/bootstrap/css/bootstrap.min.css" in html and "css/theme.css" in html
    assert 'class="wordmark' in html


@pytest.mark.parametrize("name", PUBLIC_PAGES)
def test_public_pages_shell(client, name):
    html = client.get(reverse(name)).content.decode()
    _check_shell(html)
    assert "Eligibility-first, explainable internship matching" in html


@pytest.mark.parametrize("name", STUDENT_PAGES)
def test_student_pages_shell(student_client, student, name):
    StudentProfile.objects.create(student=student, qualification="B.Tech", academic_percentage=Decimal("70"),
                                  skills=["python"])
    resp = student_client.get(reverse(name))
    assert resp.status_code == 200
    html = resp.content.decode()
    _check_shell(html)
    assert 'class="app-topbar' in html and "app-sidebar" not in html


@pytest.mark.parametrize("name", ADMIN_PAGES)
def test_admin_pages_shell(admin_client_, name):
    resp = admin_client_.get(reverse(name))
    assert resp.status_code == 200
    html = resp.content.decode()
    _check_shell(html)
    assert 'class="app-sidebar' in html


def test_active_nav_item_marked_for_current_page(student_client):
    html = student_client.get(reverse("internships:list")).content.decode()
    assert re.search(r'<a[^>]+aria-current="page"[^>]*>\s*Internships', html)


def test_no_external_urls_in_templates_or_static():
    roots = [Path(settings.BASE_DIR) / "templates", Path(settings.BASE_DIR) / "static" / "css",
             Path(settings.BASE_DIR) / "static" / "js", Path(settings.BASE_DIR) / "static" / "img"]
    offenders = []
    for root in roots:
        for f in root.rglob("*"):
            if f.suffix in {".html", ".css", ".js", ".svg"}:
                text = f.read_text(encoding="utf-8")
                for m in re.finditer(r"""(?:src|href|url)\s*[=(]\s*["']?(https?://[^"')\s>]+)""", text):
                    if "www.w3.org" not in m.group(1):
                        offenders.append(f"{f.name}: {m.group(1)}")
    assert offenders == []


def test_theme_css_floor_basics():
    css = (Path(settings.BASE_DIR) / "static" / "css" / "theme.css").read_text(encoding="utf-8")
    assert css.lstrip().startswith("/* Hallmark")
    assert "overflow-x: clip" in css and "prefers-reduced-motion" in css and ":focus-visible" in css
    assert "transition: all" not in css
    body = css.split("}", 1)[1] if ":root" in css else css
    after_tokens = css[css.index(":root"):]
    after_tokens = after_tokens[after_tokens.index("}") + 1:]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", after_tokens), "literal colours must live in :root tokens"


@pytest.mark.xfail(strict=True, reason="page templates are redesigned in PLAN Tasks 20-21; mark removed there")
def test_no_middle_dot_meta_strings_in_templates():
    hits = []
    for f in (Path(settings.BASE_DIR) / "templates").rglob("*.html"):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if " · " in line and "<title>" not in line and "· Eligo" not in line:
                hits.append(f"{f.relative_to(settings.BASE_DIR)}:{n}")
    assert hits == []
