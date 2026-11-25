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
| D-012 | 2026-11-24 | 2 | Job-role features: multi-hot canonical skills (`SkillBinarizer`, fitted on train only) |
| D-013 | 2026-11-24 | 2 | One canonical skill vocabulary + synonym map for both datasets and the LLM output |
| D-014 | 2026-11-24 | 2 | Embedding cache: `internships.npy` for imported rows, JSONField for admin-added/edited, text-hash check |
| D-015 | 2026-11-24 | 2 | Recommendations saved per run (`run_id`), never overwritten |
| D-016 | 2026-11-24 | 2 | Related internships for a career field: documented keyword map + semantic ranking |
| D-017 | 2026-11-24 | 2 | Qualification hierarchy map (Any Graduate / Any Postgraduate / specific degree / Diploma) |
| D-018 | 2026-11-24 | 2 | Tests use pytest + pytest-django with hand-written fixtures (no factory-boy) |
| D-019 | 2026-11-24 | 2 | Exam: one question per view in a single page, palette navigation, no-JS fallback = list |
| D-020 | 2026-11-24 | 2 | Sentence model kept out of git; one-command pinned-revision setup script verified against the manifest |
| D-021 | 2026-11-24 | 2 | Job-role prediction shows confidence; scope status confident / low_confidence / out_of_scope |
| D-022 | 2026-11-24 | 4 | Career skills: cleaned survey vocabulary, profile multi-select from the model's vocabulary, crosswalk suggestions |
| D-024 | 2026-11-25 | 4 | Optional LLM in the web app: skill-gap cross-check for the top 3 results; matched/missing stay deterministic |

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
- **Final distribution after cleaning (notebook run, 8,207 internships):** Any Graduate 7,966 · MBA 71 · Diploma 55 · Any Postgraduate 49 · B.Tech 32 · LLB 10 · BBA 9 · M.Tech 4 · B.Sc 3 · B.Des 2 · B.Com 2 · M.Sc 2 · MCA 2; specialisation CSE on 107. The rule table lives in `ml_core/preprocessing.py` (`_DEGREE_PATTERNS`, `_OPEN_TO_ALL`, `_CSE`), and each rule has a test built from a real row.
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
- **Caveat:** schema-constrained decoding guarantees valid JSON **syntax**, not correct **content**.
- **Live results (2026-11-25, after the pull):** on the RTX 5060 the model runs 100% on the GPU. Our exact request (`format` + `think: false`) answers in about 2.3 s warm and about 5 s cold. Without the schema `format`, Qwen3 writes 1,700–2,000 tokens of reasoning (25–36 s) even with `think: false`, which confirms that both settings are needed. Two problems found and fixed with tests: (1) the **first-ever** load after the pull exceeded the 20 s timeout (one-time disk + GPU warm-up; the fallback handled it); (2) the model returns skill **phrases** ("clean data in Python") rather than bare names, which the code dropped. `llm_items_to_vocab` now maps each item to the vocabulary (exact match, then the deterministic phrase matcher). Regression test: `test_llm_skill_phrases_mapped_to_vocab`. A web generation run with the LLM on the top 3 takes about 11 s, against about 3 s rule-based. That's why pydantic validation + normalisation through `ml_core.skills` still run, and the UI always shows which method was used.

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

## D-012 … D-019 — Phase 2 design decisions
- **Date:** 2026-11-24 · **Phase:** 2. The full alternatives and reasoning for each are in `docs/superpowers/specs/2026-11-24-eligo-design.md` §4. Summary:

| # | Chosen | Main alternative(s) rejected | Deciding criterion |
|---|---|---|---|
| D-012 | Multi-hot canonical skill vector via `SkillBinarizer` inside the Pipeline (vocabulary from train only) | TF-IDF over the raw skill string; sentence embeddings | Explainability (each feature = a skill) + leakage safety + train/inference consistency |
| D-013 | One canonical vocabulary + synonym map shared by both datasets, the profile form and the LLM output | Separate per-dataset vocabularies | Correctness: matched/missing skills would silently miss on spelling variants |
| D-014 | `internships.npy` for imported postings + `Internship.embedding` JSONField for admin-added/edited, keyed by text hash; TF-IDF on the fly | All embeddings in the DB (~30 MB JSON); re-encode at startup | Speed + correctness (stale embeddings detected by hash) |
| D-015 | Each generation is a new run (`run_id`, `generated_date`, linked attempt) | Overwrite per student | History preserved, spec §14 "stored" |
| D-016 | Career-field → title/skill keyword map, ranked semantically, filtered by gates | Similarity to the label text alone | Short labels ("Security") give unstable similarity |
| D-017 | Documented qualification hierarchy map; profile choices come from it | Free-text qualification | Gate correctness: inputs and rules share one vocabulary |
| D-018 | pytest + pytest-django + hand-written fixtures; `unittest.mock` for Ollama/HTTP | factory-boy + pytest-mock | Locked stack: no new dependencies for little gain |
| D-019 | One question per view inside one page, palette jumps, autosave per answer, no-JS fallback = full list | Server page per question; scroll-only list | Fits the palette design, fewer requests, graceful degradation |

## D-020 — Sentence model: out of git, one-command setup
- **Date:** 2026-11-24 · **Phase:** 2 (Krishna's instruction: no Git LFS)
- **Options:** (1) commit the ~90 MB model with Git LFS: rejected by Krishna (LFS bandwidth quotas, an extra tool for anyone cloning); (2) commit it as a normal blob: under GitHub's 100 MB hard limit but bloats every clone and the history; (3) **git-ignore `artifacts/models/sentence_model/`** and provide a setup step.
- **Chosen:** option 3 with two ways to get the model: run the notebook (it saves the model), or run `.\.venv\Scripts\python.exe scripts\setup_sentence_model.py`. The script downloads `sentence-transformers/all-MiniLM-L6-v2` at a **pinned Hugging Face revision** (commit hash in `ml_core/config.py`), saves it with `create_model_card=False`, and verifies every file against the SHA-256 hashes in `artifacts/manifest.json`. Internet is needed once; after that everything runs offline.
- **Safety:** rule 14 still holds. Django loads the model only from `artifacts/`, and only if the manifest check passes. If the folder is missing, the banner names the setup command instead of crashing. If a fresh download isn't byte-identical to the notebook's save (checked in Phase 3), the manifest hashes only the weight and config files and this note gets updated.
- **README:** setup step added (PLAN Task 23).
- **Phase 3 finding (2026-11-24):** the first check failed only on `tokenizer.json`. `SentenceTransformer.encode()` writes runtime padding/truncation state into the tokenizer, so a model saved *after* encoding isn't byte-identical to a fresh download (weights and every other file were identical). Fix: the notebook saves the pristine pinned model first, then reloads it from disk and encodes with that copy. Embeddings now come from exactly the files Django loads, and `setup_sentence_model.py` reproduces the folder byte-for-byte (verified: "Sentence model verified against manifest.json").

## D-021 — Job-role confidence and model scope
- **Date:** 2026-11-24 · **Phase:** 2 (Krishna's instruction)
- **Why:** the model only knows 6 CS career fields and the skills in its training vocabulary. A marketing student would otherwise get a confident-looking but meaningless "Development".
- **Rule** (`ml_core.job_role.scope_status`, thresholds stored in `feature_schema.json` → `scope`):
  - `out_of_scope`: fewer than `min_known_skills` (default 2) of the student's skills are in the model's vocabulary, **or** less than `min_coverage` (default 50%) of their skills are. With zero known skills the model isn't called at all.
  - `low_confidence`: in scope, but the max class probability is below `min_confidence` (default 0.50; chance level for 6 classes is about 0.17).
  - `confident`: otherwise.
- **UI:** the confidence % is always shown. Only `confident` gets the "Predicted job role" hero. The other two states say plainly: "Your profile is mostly outside what this model covers (6 computer-science career fields)…" or "Low confidence…", list the known vs unknown skills, and show the closest field labelled tentative.
- **Defaults vs data:** the defaults above were placeholders until Phase 3. The notebook then printed the real test-set accuracy of the best model (Random Forest, test n = 374):

  | Max class probability | Rows | Accuracy |
  |---|---|---|
  | < 0.4 | 27 | 0.519 |
  | 0.4–0.5 | 33 | 0.667 |
  | 0.5–0.6 | 65 | 0.846 |
  | 0.6–0.8 | 167 | 0.964 |
  | ≥ 0.8 | 82 | 0.988 |

  | Skills the model knows | Rows | Accuracy |
  |---|---|---|
  | 1 | 10 | 0.700 |
  | 2 | 33 | 0.818 |
  | 3+ | 331 | 0.903 |

- **Superseded by the Phase 4 retrain (D-022 cleaned vocabulary), 2026-11-24.** The tables above are from the Phase 3 model. After the vocabulary clean-up (test n = 330):

  | Max class probability | Rows | Accuracy |
  |---|---|---|
  | < 0.4 | 8 | 0.250 |
  | 0.4–0.5 | 23 | 0.478 |
  | 0.5–0.6 | 34 | 0.706 |
  | 0.6–0.8 | 77 | 0.831 |
  | ≥ 0.8 | 188 | 0.952 |

  | Career skills the model knows | Rows | Accuracy |
  |---|---|---|
  | 1 | 9 | 0.444 |
  | 2 | 24 | 0.625 |
  | 3+ | 297 | 0.879 |

- **Final thresholds (Phase 4): `min_confidence = 0.5`, `min_known_skills = 3`, `min_coverage = 0.5`.** Confidence still splits cleanly: 0.419 accuracy below 0.5 vs 0.893 at or above it. Two known skills now give only 0.625, against 0.879 for three or more, so the numbers argue for raising `min_known_skills` from 2 to 3 (the rule above said to keep the defaults "unless the numbers argue otherwise"). The profile form asks for at least 3 career skills.
- *(Phase 3 values, for the record: `min_confidence = 0.5`, `min_known_skills = 2`, `min_coverage = 0.5`.)* Below 0.5 confidence, accuracy falls to 0.600 (60 rows), against 0.946 at or above it (314 rows). That's a clear break, so "low confidence" means something real. One known skill gives 0.700 over just 10 rows; two or more give 0.82+. `min_coverage` can't be checked against the test set, because test rows only contain skills from the training data. It stays a product rule: if most of a student's skills are unknown to the model, the profile is mostly outside its scope.
- **Tests:** `test_scope_status_rules` (parametrised boundaries), `test_demo_cs_profile_confident_and_correct` (real artifacts), `test_scope_status_no_known_skills_no_model_call`, `test_scope_status_mostly_unknown_is_out_of_scope`, `test_scope_status_thresholds_read_from_schema`, `test_explain_job_role_low_confidence_has_scope_message`, `test_prediction_view_out_of_scope_message`, `test_low_confidence_not_shown_as_confident`, `test_confident_prediction_shows_confidence_percentage`.

## D-022 — Career skills: cleaned vocabulary, model-vocabulary multi-select, crosswalk
- **Date:** 2026-11-24 · **Phase:** 4 (Krishna's instruction, after Phase 3 showed `python` isn't in the model's vocabulary)
- **Problem:** the job-role model's features are the student survey's own skill names. Students type free-text skills ("Python", "TensorFlow"), so most of them were unknown to the model and predictions came out low-confidence. Reviewing the 268 model features also showed many spelling variants of one skill ("interpersonnal skills", "android app make", five spellings of "web based project develop"). A multi-select built from those raw strings would look unprofessional, and splitting one skill across several features weakens the model.
- **Options:**
  1. Map free-text skills to model features automatically, with no student input: hidden and hard to explain, and wrong mappings become wrong predictions.
  2. A multi-select over the raw 268-feature vocabulary: honest but noisy (typos as options).
  3. **Clean the survey vocabulary at the source** (a written variant → canonical map, `SURVEY_SYNONYMS` + compound splits in `ml_core/skills.py`, built from the real 268 strings), retrain, then offer the cleaned vocabulary as a **"Career skills" multi-select labelled "Skills the job-role model understands"**. The prediction uses only these. A small **crosswalk** (`CAREER_SKILL_CROSSWALK` in `ml_core/job_role.py`, e.g. `python` → `programming languages`, `figma` → `ui/ux design`, `tensorflow` → `deep learning`) only *pre-suggests* career skills from the free-text skills, and the student confirms them. Free-text skills stay for internship matching.
- **Chosen:** option 3. Spec §2 asks for exactly this kind of skill-feature processing, and the student keeps control over what the model sees.
- **Effect on the model (real numbers, test split):** rows used went from 1,868 to 1,646, because more rows became exact duplicates after the variants were merged and were removed before splitting. Random Forest test macro-F1 went from 0.9107 to **0.8787** (accuracy 0.8904 → 0.8485); Decision Tree macro-F1 0.8604 → 0.8048. The test sets differ, so the numbers aren't directly comparable. The earlier score was partly inflated: two spellings of the same student row could land one in train and one in test. The new numbers are the honest ones.
- **DEMO profiles** now live in one shared module, `ml_core/demo.py` (used by the notebook and by `seed_demo`), each with free-text skills and career skills. The DEMO CS profile predicts **Artificial Intelligence at 95%, scope confident** (test `test_demo_cs_profile_confident_and_correct`, against the real artifacts).
- **Guards:** `test_crosswalk_targets_exist_in_schema_vocab` fails if a crosswalk target isn't a real model feature; `test_demo_career_skills_all_known_to_model` does the same for the DEMO profiles.

## D-024 — Optional LLM in the web app: a cross-check, not the score
- **Date:** 2026-11-25 · **Phase:** 4 (Task 16)
- **Question:** spec §13 says to "integrate optional LLM skill extraction". Where should its output go?
- **Options:**
  1. Let the LLM decide matched/missing skills, and with them the skill score: the score would then depend on a non-deterministic model, breaking "explanations from computed values" and the reproducibility of a ranking.
  2. **The deterministic, normalised comparison of required skills decides matched/missing and the skill score. The LLM reads each top result's text and reports the skills it finds missing as a second opinion**, stored in `explanation.llm_gap` and shown as "The local LLM also read the description and found missing: …". Every row stores `analysis_method` (`llm` / `rule_based`).
- **Chosen:** option 2, run for the **top 3** results only (`LLM_TOP_K = 3`). Each local call takes about 1–2 s on the GPU, so all 10 would make every click slow.
- **Availability:** `ollama_available()` now returns true only when the server answers **and** the configured model is installed. With the server up but the model still downloading, each LLM call used to fail slowly (7.6 s of a 9.7 s generation run). After the fix, plus cached rule-based patterns, a real generation run over 8,207 internships takes about 3 s.
