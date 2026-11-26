"""Phase 6.5 review fixes (Krishna, 2026-11-26): layout, polish and chart behaviour. Fixtures only."""
import json
import re
import struct
import zlib
from datetime import timedelta
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from assessments import services as exam_services
from assessments.models import Assessment, Attempt, Question
from internships.models import Internship
from recommendations import services
from recommendations.models import InternshipRecommendation
from students.models import StudentProfile

pytestmark = pytest.mark.django_db
CSS = (Path(settings.BASE_DIR) / "static" / "css" / "theme.css").read_text(encoding="utf-8")


def _css_block(selector_start):
    """The text of the @media block that contains `selector_start` (for scoped CSS assertions)."""
    i = CSS.index(selector_start)
    return CSS[CSS.rfind("@media", 0, i):i + 400]


def _profile(student, **kw):
    base = dict(qualification="B.Tech", specialization="CSE", academic_percentage=Decimal("75"),
                skills=["python", "sql"], career_skills=["machine learning", "python", "statistics"])
    base.update(kw)
    return StudentProfile.objects.create(student=student, **base)


def _exam(n=5, minutes=10, name="Aptitude (fixture)"):
    a = Assessment.objects.create(assessment_name=name, qualification="Any Graduate", duration_minutes=minutes,
                                  status="ACTIVE")
    for i in range(n):
        Question.objects.create(assessment=a, question_text=f"Q{i}?", option_a="a", option_b="b", option_c="c",
                                option_d="d", correct_option="A")
    return a


def _finished(student, score="80", result="QUALIFIED"):
    a = _exam()
    now = timezone.now()
    return Attempt.objects.create(student=student, assessment=a, start_time=now - timedelta(minutes=5), deadline=now,
                                  submission_time=now, status="SUBMITTED", total_marks=5, obtained_marks=4,
                                  score_percentage=Decimal(score), result=result)


def _internship(**kw):
    base = dict(company_name="Acme (fixture)", internship_title="Data Science", job_role="Data Science",
                description="d", required_qualification="Any Graduate", required_skills=["python"],
                location="Pune", status="ACTIVE")
    base.update(kw)
    return Internship.objects.create(**base)


class _Cells(HTMLParser):
    """Collects every body <td> of every table: (table classes, td attributes)."""
    def __init__(self):
        super().__init__()
        self.table_classes, self.in_tbody, self.cells = [], False, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.table_classes.append(a.get("class", ""))
        elif tag == "tbody":
            self.in_tbody = True
        elif tag == "td" and self.in_tbody:
            self.cells.append((self.table_classes[-1], a))

    def handle_endtag(self, tag):
        if tag == "tbody":
            self.in_tbody = False


def _assert_tables_stack(html):
    p = _Cells()
    p.feed(html)
    assert p.table_classes, "no table on the page"
    assert all("table-stack" in c for c in p.table_classes), p.table_classes
    unlabeled = [a for _, a in p.cells if "data-label" not in a and "colspan" not in a]
    assert not unlabeled, unlabeled[:3]


# --- found while taking the check shots: browsers kept stale JS/CSS after an update ------------------
def test_own_assets_carry_a_content_hash_version(student_client):
    import hashlib
    html = student_client.get(reverse("students:dashboard")).content.decode()
    for rel in ("css/theme.css", "js/ui.js"):
        digest = hashlib.sha256((Path(settings.BASE_DIR) / "static" / rel).read_bytes()).hexdigest()[:12]
        assert f"/static/{rel}?v={digest}" in html, rel
    templates = Path(settings.BASE_DIR) / "templates"
    unversioned = [f.name for f in templates.rglob("*.html")
                   if re.search(r"\{% static '(css|js)/", f.read_text(encoding="utf-8"))]
    assert unversioned == [], "use {% asset %} for our own CSS/JS"


# --- 1. mobile tables become stacked cards -------------------------------------------------------
def test_stacked_table_css_for_phones():
    block = _css_block(".table-stack td::before")
    assert "max-width: 47.98rem" in block and "attr(data-label)" in block


@pytest.mark.parametrize("name", ["adminpanel:students", "adminpanel:results", "adminpanel:recommendations",
                                  "internships:admin_list", "assessments:admin_list", "adminpanel:dashboard"])
def test_admin_tables_label_every_cell(admin_client_, student, name):
    _profile(student)
    attempt = _finished(student)
    i = _internship()
    InternshipRecommendation.objects.create(student=student, internship=i, assessment_attempt=attempt, skill_match_score=0.3,
                                            content_similarity_score=0.5, semantic_similarity_score=0.5,
                                            final_match_score=0.45, recommendation_rank=1, recommendation_reason="r")
    _assert_tables_stack(admin_client_.get(reverse(name)).content.decode())


def test_student_attempts_table_labels_every_cell(student_client, student):
    _profile(student)
    _finished(student)
    _assert_tables_stack(student_client.get(reverse("assessments:list")).content.decode())


# --- 2. mobile admin top bar ---------------------------------------------------------------------
def test_admin_account_links_move_into_the_menu_on_phones(admin_client_):
    html = admin_client_.get(reverse("adminpanel:dashboard")).content.decode()
    sidebar = html.split('id="app-sidebar"', 1)[1].split("</aside>", 1)[0]
    assert reverse("accounts:password_change") in sidebar and reverse("accounts:logout") in sidebar
    assert "Change password" in sidebar and "app-sidebar__account" in sidebar
    block = _css_block(".admin-topbar .app-user")
    assert "display: none" in block
    assert "text-overflow: ellipsis" in CSS[CSS.index(".admin-topbar .breadcrumb {"):][:400]


# --- 3 + 5. sticky footer, one container width ---------------------------------------------------
def test_footer_sticks_to_the_bottom_and_scrollbar_never_shifts_layout():
    assert re.search(r"\.app-shell \{[^}]*min-height: 100vh[^}]*flex-direction: column", CSS)
    assert re.search(r"\.admin-content \{[^}]*flex: 1 0 auto", CSS)
    assert re.search(r"html \{[^}]*scrollbar-gutter: stable", CSS)


# --- 4. mobile exam: question first ----------------------------------------------------------------
def test_exam_palette_comes_after_the_question_on_phones():
    block = _css_block(".palette { position: static")
    assert "order: -1" not in block and "order: 1" in block


# --- 6. result stats on phones ---------------------------------------------------------------------
def test_result_stats_stay_in_one_aligned_row_on_phones():
    block = _css_block(".result-stats { grid-template-columns: repeat(3")
    assert "max-width: 40rem" in block


# --- 11. career-skill chips --------------------------------------------------------------------------
def test_career_skill_picker_has_a_selected_chips_area(student_client, student, fake_artifacts):
    html = student_client.get(reverse("students:profile_edit")).content.decode()
    assert "data-skill-chips" in html and 'aria-live="polite"' in html


# --- 13. internship facts ----------------------------------------------------------------------------
def test_internship_detail_facts(student_client, student):
    _profile(student)
    i = _internship(minimum_academic_percentage=0, start_date="Immediately", eligibility_criteria="")
    html = student_client.get(reverse("internships:detail", args=[i.pk])).content.decode()
    assert re.search(r"<dt>Minimum academic %</dt><dd>Not specified</dd>", html)
    assert re.search(r"<dt>Starts</dt><dd>Immediately</dd>", html)
    assert "Eligibility criteria" not in html and "Start:" not in html


# --- 14. qualification badge -------------------------------------------------------------------------
def test_qualification_badge_only_when_specific(student_client, student):
    _profile(student)
    _internship(internship_title="Open Role (fixture)")
    _internship(internship_title="CSE Role (fixture)", specialization="CSE")
    _internship(internship_title="MBA Role (fixture)", required_qualification="MBA")
    html = student_client.get(reverse("internships:list")).content.decode()
    badges = re.findall(r'<span class="chip chip--neutral qual-badge">(.*?)</span>\s*</li>', html, re.S)
    texts = ["|".join(re.findall(r'qual-badge__part">([^<]*)<', b)) for b in badges]
    assert sorted(texts) == ["Any Graduate|CSE", "MBA"]
    assert ".qual-badge__part + .qual-badge__part::before" in CSS


# --- 15. most recommended chart ----------------------------------------------------------------------
def _rows(student, attempt, spec):
    """spec: {internship: number of runs it appears in}; runs = max count."""
    import uuid
    runs = [uuid.uuid4() for _ in range(max(spec.values()))]
    for internship, n in spec.items():
        for run in runs[:n]:
            InternshipRecommendation.objects.create(
                student=student, internship=internship, assessment_attempt=attempt, run_id=run, skill_match_score=0.3,
                content_similarity_score=0.5, semantic_similarity_score=0.5, final_match_score=0.4,
                recommendation_rank=1, recommendation_reason="r")


def _chart(html):
    m = re.search(r'<script id="recs-chart-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def test_recommended_chart_labels_title_at_company(admin_client_, student):
    attempt = _finished(student)
    a = _internship(internship_title="ML Intern", company_name="Acme")
    b = _internship(internship_title="ML Intern", company_name="Beta")
    _rows(student, attempt, {a: 3, b: 1})
    data = _chart(admin_client_.get(reverse("adminpanel:dashboard")).content.decode())
    assert data == {"labels": ["ML Intern @ Acme", "ML Intern @ Beta"], "values": [3, 1]}


@pytest.mark.parametrize("spec", [{"a": 2, "b": 1}, {"a": 3, "b": 3}])
def test_recommended_chart_needs_enough_varied_data(admin_client_, student, spec):
    attempt = _finished(student)
    objs = {k: _internship(internship_title=f"Role {k}") for k in spec}
    _rows(student, attempt, {objs[k]: n for k, n in spec.items()})     # 2 runs, or 3 runs with equal counts
    html = admin_client_.get(reverse("adminpanel:dashboard")).content.decode()
    assert _chart(html) is None and "Not enough data yet" in html


# --- 16. ML figures ----------------------------------------------------------------------------------
def _png(path, w, h):
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))  # noqa: E731
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def test_wide_figures_span_the_page_and_open_full_size(admin_client_, fake_artifacts):
    from ml_core.artifacts import write_manifest
    _png(fake_artifacts / "figures" / "wide_panels.png", 300, 100)
    _png(fake_artifacts / "figures" / "square.png", 100, 100)
    write_manifest(fake_artifacts, best_model_name="RandomForestClassifier", model_version="1", sentence_model_revision="x")
    services.reset_bundle_cache()
    html = admin_client_.get(reverse("adminpanel:ml")).content.decode()
    wide = re.search(r'<figure class="([^"]*)"[^>]*>\s*<a href="([^"]+wide_panels\.png)"', html)
    square = re.search(r'<figure class="([^"]*)"[^>]*>\s*<a href="([^"]+square\.png)"', html)
    assert wide and "figure--wide" in wide.group(1) and square and "figure--wide" not in square.group(1)
    assert 'data-enlarge' in html


# --- 17. not-qualified ring colour -------------------------------------------------------------------
def test_not_qualified_result_ring_uses_the_warning_colour(student_client, student):
    _profile(student)
    a = _exam(n=5)
    attempt = exam_services.start_or_resume(student, a, timezone.now())
    exam_services.submit(attempt.pk, student, {q.pk: "A" for q in a.questions.all()[:3]}, timezone.now())
    html = student_client.get(reverse("assessments:result", args=[attempt.pk])).content.decode()
    assert "score-ring score-ring--lg score-ring--warn" in html and 'class="score-ring__marker"' in html
    assert ".score-ring--warn" in CSS and "var(--missing)" in CSS[CSS.index(".score-ring--warn"):][:200]


def test_qualified_result_ring_keeps_amber(student_client, student):
    _profile(student)
    attempt = _finished(student)
    attempt.answers.all()
    html = student_client.get(reverse("assessments:result", args=[attempt.pk])).content.decode()
    assert "score-ring--warn" not in html


# --- 18. small polish ----------------------------------------------------------------------------------
def test_timer_pill_reads_time_left(student_client, student):
    _profile(student)
    a = _exam(n=3, minutes=2)
    url = student_client.post(reverse("assessments:start", args=[a.pk])).url
    html = student_client.get(url).content.decode()
    assert re.search(r'<span id="timer-value">\d+:\d\d left</span>', html)
    js = (Path(settings.BASE_DIR) / "static" / "js" / "timer.js").read_text(encoding="utf-8")
    assert '" left"' in js and "bi-exclamation-triangle" in js


def test_student_nav_says_change_password(student_client):
    html = student_client.get(reverse("students:dashboard")).content.decode()
    nav = html.split('id="student-nav"', 1)[1].split("</nav>", 1)[0]
    assert ">Change password</a>" in nav


def test_row_action_buttons_sit_on_the_link_baseline():
    assert re.search(r"\.row-actions \{[^}]*align-items: baseline", CSS)
    assert re.search(r"\.row-actions \.btn-link \{[^}]*vertical-align: baseline", CSS)


def test_match_ring_has_an_info_tooltip(student_client, student, ai_bundle):
    _profile(student)
    _finished(student)
    services.generate_recommendations(student)
    html = student_client.get(reverse("recommendations:list")).content.decode()
    assert 'data-bs-toggle="tooltip"' in html and "What the match % means" in html
    assert "not a chance of selection" in html
