# Decisions log — Eligo

Every choice the spec leaves open is recorded here: what was chosen, the alternatives considered, and why.
Criteria, in priority order (from `CLAUDE.md`): **spec compliance > correctness > offline/Windows-friendly > looks professional > simplicity.**

| # | Date | Phase | Decision |
|---|---|---|---|
| D-001 | 2026-11-22 | 0 | Install Python 3.12 per-user with winget |
| D-002 | 2026-11-22 | 0 | Vendored file set (minified + source maps, Chart.js UMD) |
| D-003 | 2026-11-22 | 0 | Font subsets: latin + latin-ext, woff2 only |
| D-004 | 2026-11-22 | 0 | Third-party project skills are git-ignored and pinned via `skills-lock.json` |
| D-005 | 2026-11-24 | 1 | Job-role training data: Student Career Dataset (Mendeley 4spj4mbpjr v2) |
| D-006 | 2026-11-24 | 1 | Internship listings: Internship Opportunities in India (2025) (Kaggle) |
| D-007 | 2026-11-24 | 1 | Qualification fields: derive from `Education` by documented rule, neutral defaults otherwise |
| D-008 | 2026-11-24 | 1 | Assessment score is an eligibility gate only, not a model feature |
| D-009 | 2026-11-24 | 1 | Ollama model: `qwen3:4b` with `think: false` (fallback option `qwen2.5:3b`) |
| D-010 | 2026-11-24 | 1 | UI kit: plain Bootstrap 5 + custom `theme.css` (not Tabler) |
| D-011 | 2026-11-24 | 1 | Duplicate-submission guard on SQLite: conditional UPDATE inside `atomic()` |

---

## D-001 — Install Python 3.12 per-user with winget
- **Date:** 2026-11-22 · **Phase:** 0, step 1
- **Context:** Only Python 3.14 was installed. The spec locks the stack to Python 3.12.
- **Options:**
  1. `winget install Python.Python.3.12 --scope user`: official python.org installer (hash-verified by winget), per-user, no admin prompt, picked up by `py -3.12` immediately.
  2. Krishna downloads the installer from python.org manually and ticks "Add to PATH".
  3. Use the existing 3.14: rejected, breaks spec compliance (and torch / sentence-transformers wheel support lags new Python releases).
- **Chosen:** Option 1 (Krishna picked it when asked). Installed **3.12.10**. Python 3.14 stays as the system default; the project always uses `py -3.12` / the `.venv`.

## D-002 — Vendored frontend file set
- **Date:** 2026-11-22 · **Phase:** 0, step 7
- **Options:**
  1. Copy whole `dist/` folders: simple, but adds ~10 MB of unused ESM/RTL/grid builds.
  2. Copy only what the templates will load: `bootstrap.min.css`, `bootstrap.bundle.min.js` (includes Popper for dropdowns/modals), Bootstrap Icons `min.css` + font, Chart.js `chart.umd.min.js`, plus each library's source map and LICENSE.
- **Chosen:** Option 2. The UMD build of Chart.js works from a plain `<script>` tag, so no bundler or ES-module import maps are needed (rule 18: no build step). Source maps are kept so browser devtools stay readable during development, and LICENSE files are kept for licence compliance. Exact versions are recorded in `static/vendor/VERSIONS.json`: Bootstrap 5.3.9, Bootstrap Icons 1.13.2, Chart.js 4.6.1, @fontsource Inter 5.3.0, Plus Jakarta Sans 5.3.0. Total vendored size: 3.1 MB.
- **Check:** the vendored CSS contains no remote `url()`. The only `http(s)` strings are licence comments and the SVG XML namespace.

## D-003 — Font subsets: latin + latin-ext, woff2 only
- **Date:** 2026-11-22 · **Phase:** 0, step 7
- **Context:** BUILD_PROMPT asks for woff2 at weights 400/500/600/700. Stipends will be shown in rupees, and the **₹ sign (U+20B9) is in the `latin-ext` subset**, not `latin` (confirmed from `@fontsource/*/unicode.json`).
- **Options:**
  1. latin only: smallest, but ₹ would fall back to a system font and look mismatched next to the digits.
  2. latin + latin-ext, each declared with its `unicode-range` in a generated `static/vendor/fonts/fonts.css`: the browser downloads the latin-ext file only on pages that actually contain one of its characters.
  3. Full variable fonts: larger, and not needed for 4 weights.
- **Chosen:** Option 2. woff2 only (every supported browser, Chrome/Edge, reads woff2). Fonts are SIL OFL 1.1, and the licence files are copied alongside.

## D-004 — Third-party project skills are git-ignored
- **Date:** 2026-11-22 · **Phase:** 0, step 5
- **Context:** `npx skills add kjnez/claude-code-django` (the repo has moved to `waldencui/claude-code-django`) copied 15 skills into `.claude/skills/` and wrote `skills-lock.json` (commit `ef057aa…` + per-skill hashes). One upstream skill (`ticket`) was skipped by the installer because of a YAML error in its own file, which doesn't affect us. Of the 15, the ones relevant to this project are `django-models`, `django-forms`, `django-templates`, `pytest-django-patterns` and `systematic-debugging`. `celery-patterns` and `htmx-patterns` are not used (no Celery; the spec fixes the frontend to vanilla JS).
- **Options:**
  1. Commit `.claude/skills/`: a fresh clone has them, but it puts third-party dev tooling inside a repo that goes public in Phase 7.
  2. Git-ignore `.claude/skills/`, commit `skills-lock.json` (pins source + commit + hashes so they can be reinstalled exactly).
- **Chosen:** Option 2. Skills are developer tooling, not part of the deliverable, and the lock file keeps them reproducible.

## D-005 — Job-role training data: Student Career Dataset
- **Date:** 2026-11-24 · **Phase:** 1, step 3A
- **Options evaluated** (each verified through the Mendeley public API: licence, file, SHA-256; then downloaded and profiled with real computation):

  | Candidate | Licence | Rows | Real? | Form-collectible features? | Signal check (5-fold CV) |
  |---|---|---|---|---|---|
  | **Student Career** `4spj4mbpjr` v2 | CC BY 4.0 | 4,076 (2,176 unique) | Yes, student survey | Yes, skills | LR acc **0.895** vs baseline 0.261 |
  | Student Skill Gap `rv6scbpd7v` | CC BY 4.0 | 500 | Looks generated | Yes | LR acc 0.148 vs baseline 0.186; all chi-square p > 0.19 → **no signal** |
  | CareerMap `5z68cvxssn` | CC BY 4.0 | 9,179 | Augmented (exactly 540/role) | No, 10 personality-test features | not needed, rejected on criteria 3 + 5 |
  | Career Path Prediction `cns7h4b9g7` | CC BY 4.0 | 15,000 | **Synthetic** (label = random pick within interest group) | Partly | RF acc 0.317 vs baseline 0.051, about chance within group |
- **Chosen:** Student Career. It is the only candidate that is real **and** has signal **and** whose features our profile form collects (selection criterion 3, the one that matters most).
- **Trade-off accepted:** skills are the only feature, so the model can't use academic % or qualification (stated on the prediction page and in README). Training on a synthetic dataset with more columns would have looked richer but produced meaningless predictions, which conflicts with hard rule 6.
- **Note:** the CV numbers above are a selection check only. Phase 3 produces the real reported metrics with a proper train/test split.

## D-006 — Internship listings: Internship Opportunities in India (2025)
- **Date:** 2026-11-24 · **Phase:** 1, step 3B
- **Options evaluated** (column lists from Kaggle's public Croissant metadata):
  1. **Internship Insights** (`aayush9119/internshala-dataset`, Apache 2.0, the suggested main candidate): columns `Title, Company Name, Location, Start Date, Duration, Stipend, Status, Links`. **No skills, education or description**, so skill matching, the qualification gate and TF-IDF over requirements can't work. Rejected.
  2. **Internship Opportunities in India (2025)** (`jayaantanaath`, MIT, 8,485 postings): `profile, company, Location, Start Date, Stipend, Duration, Apply by Date, Offer, Education, Skills, Perks`. It has both **Skills** and **Education**.
  3. `himanshu9648/internshala-internships-analysis` (Apache 2.0, ~7.7k): has skills but no company, education or duration.
  4. AICTE Government Internship Dataset (MIT, ~2k): no skills or education.
  5. `logiover/internshala-scraper-sample-data` (HF, CC BY 4.0): has real descriptions, but only 50 rows.
- **Chosen:** option 2. It is the only one covering required skills + required education + stipend + duration + location at scale.
- **Gap handled transparently:** no description column, so `description` is composed from the posting's own fields and flagged `description_derived` (DATASETS.md).
- **Needs Krishna:** Kaggle requires a login to download (ASK KRISHNA).

## D-007 — Qualification fields and dataset-relative deadline
- **Date:** 2026-11-24 · **Phase:** 1, step 4
- **Context:** the chosen internship data has an `Education` column but no `specialization` split and no `minimum_academic_percentage`. Its `Apply by Date` values are 2025 dates.
- **Options:** (a) derive the fields with a transparent rule and a `derived_fields` note per record; (b) neutral defaults ("Any Graduate", 0%) that admins can edit.
- **Chosen: (a) where the source has the information, (b) where it doesn't.** Never a silent guess.
  - `required_qualification` / `specialization`: parsed from `Education` with a documented keyword → qualification map in `ml_core/preprocessing.py` (e.g. "B.Tech", "B.E." → B.Tech/B.E.; "Computer Science" → specialization CSE). Empty or unparseable values → "Any Graduate" / no specialization. Every record stores `derived_fields` listing which values came from a rule or a default.
  - `minimum_academic_percentage`: not in the source → **0% default** (gate always passes), listed in `derived_fields`, editable by admins.
  - Deadline gate: deadlines are a 2025 snapshot, so the gate compares against `REFERENCE_DATE` in `ml_core/config.py` (default **2025-09-28**, the last scrape day confirmed from `Date Time`; shown in the UI). Admin-added internships use real dates against today. Without this, every imported internship would fail the deadline gate on day one.
- **Confirmed on load (2026-11-24):** `Education` is "Not Specified" on 6,539 of 8,483 rows (77%) → "Any Graduate". Of the 1,944 specified values, 1,139 mention a degree or qualification keyword (rule-parsed) and 805 hold other text such as location limits or duties (→ "Any Graduate", text kept as an eligibility note). The final keyword → qualification table is written in Phase 3 from these real values.

## D-008 — Assessment score: eligibility gate only
- **Date:** 2026-11-24 · **Phase:** 1, step 5
- **Rule (BUILD_PROMPT):** use assessment score as a model feature only if the training data has a comparable column.
- **Finding:** the Student Career Dataset has only `Skill` and `Career`. No assessment or test-score column exists.
- **Chosen:** the assessment (score strictly > 60%) is an **eligibility gate for recommendations only**. The job-role model uses skills only. The prediction page says: "This model was trained on skills only. Your assessment score controls internship eligibility but is not a model input, because the public training data has no comparable score."

## D-009 — Ollama model: `qwen3:4b`
- **Date:** 2026-11-24 · **Phase:** 1, step 6 (**decided now, pull is PENDING – Ollama**, needs Krishna's approval)
- **Criteria:** reliable JSON with schema-constrained output, under ~3 GB, fast on a laptop, licence OK for a public repo.

  | Model | Size (Q4) | Licence | Evidence on JSON / extraction |
  |---|---|---|---|
  | **qwen3:4b** | ~2.5 GB | Apache 2.0 | Leads Llama 3.2 3B and Gemma 3 4B on tool calling and NER in a published comparison (Distil Labs). Its thinking mode can pollute output, but Ollama's `think: false` disables it and puts any reasoning in a separate `message.thinking` field (Ollama docs via Context7). |
  | qwen2.5:3b | ~1.9 GB | Qwen Research Licence (non-commercial) | Reported to work where gemma3:4b failed on long-prompt schema extraction (ollama issue #19427). |
  | llama3.2:3b | ~2.0 GB | Llama 3.2 Community Licence | Fastest (~56 tok/s in one benchmark), weakest on extraction comparisons. |
  | phi3.5 | ~2.2 GB | MIT | Mixed reports on JSON adherence. |
  | gemma3:4b | ~3.3 GB | Gemma terms | Over 3 GB; documented empty `{}` output on long extraction prompts with a schema (ollama issue #19427). |
- **Chosen:** `qwen3:4b`, called with `format=<JSON schema>`, `think: false`, `temperature: 0`, ~20 s timeout, then pydantic validation, one retry, then rule-based fallback. `qwen2.5:3b` is recorded in `llm_config.json` as the alternative if live testing shows problems.
- **Caveat:** schema-constrained decoding guarantees valid JSON **syntax**, not correct **content**. That's why pydantic validation + normalisation through `ml_core.skills` still run, and the UI always shows which method was used.

## D-010 — UI kit: plain Bootstrap 5 + `theme.css`
- **Date:** 2026-11-24 · **Phase:** 1, step 7
- **Checks run on Tabler (`@tabler/core` 1.7.5):** MIT ✅ · offline-safe ✅ (fetched `tabler.min.css`: no `@import`, no remote `url()`) · `tabler.min.css` alone is **684 KB** vs Bootstrap's ~230 KB, and the npm package is 24.8 MB unpacked. Tabler ships its own Bootstrap build, so it **replaces** our vendored Bootstrap and is re-skinned through its own `--tblr-*` variables.
- **Options compared** (criteria order: spec > correctness > offline > professional > simple):
  - Spec / correctness / offline: tie, both are Bootstrap 5 and both work offline.
  - Professional: Tabler gives polished shells faster. But our design system is bespoke (navy/amber govt-tech look, score ring, stepper, exam palette), so nearly every Tabler surface would need overriding, and its default dense-SaaS look runs against spec §15 "avoid complex dashboards".
  - Simplicity: plain Bootstrap wins, with one theme layer (`theme.css` over `--bs-*`), ~3× less CSS and no second variable system.
- **Chosen:** plain Bootstrap 5 + `theme.css`. Tabler (and 21st.dev) stay **inspiration only** for layout shells such as the sidebar and page header. Tabler is not installed.
- **Implementation note from the Bootstrap 5.3 docs:** `.btn-primary` sets its own local `--bs-btn-*` colours, so changing `--bs-primary` alone doesn't recolour buttons. `theme.css` must redefine the `.btn-primary` / `.btn-outline-primary` variables too.

## D-011 — Duplicate-submission guard on SQLite
- **Date:** 2026-11-24 · **Phase:** 1 (finding from Context7 Django 5.2 docs; implemented in Phase 4)
- **Finding:** Django docs: "Using `select_for_update()` on backends which do not support `SELECT ... FOR UPDATE` (such as SQLite) will have no effect." Hard rule 10 asks for `select_for_update`, but on SQLite it is a silent no-op.
- **Options:** (1) rely on `select_for_update` alone: not safe on SQLite; (2) keep `select_for_update()` (works if the DB is ever switched) **and** finalise with a conditional update inside `transaction.atomic()`: `Attempt.objects.filter(pk=…, status=IN_PROGRESS).update(status=…)`. The UPDATE is atomic in SQLite (database-level write lock), and a return value of 0 means someone else already submitted → reject as duplicate.
- **Chosen:** option 2. Hard rule 10 is still met (atomic status check + `select_for_update`), and it's actually correct on SQLite. A concurrency test in Phase 6 proves it.
