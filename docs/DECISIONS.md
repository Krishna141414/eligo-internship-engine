# Decisions log — Eligo

Every choice the spec leaves open is recorded here: what was chosen, the alternatives considered, and why.
Criteria, in priority order (from `CLAUDE.md`): **spec compliance > correctness > offline/Windows-friendly > looks professional > simplicity.**

| # | Date | Phase | Decision |
|---|---|---|---|
| D-001 | 2026-11-22 | 0 | Install Python 3.12 per-user with winget |
| D-002 | 2026-11-22 | 0 | Vendored file set (minified + source maps, Chart.js UMD) |
| D-003 | 2026-11-22 | 0 | Font subsets: latin + latin-ext, woff2 only |
| D-004 | 2026-11-22 | 0 | Third-party project skills are git-ignored and pinned via `skills-lock.json` |

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
