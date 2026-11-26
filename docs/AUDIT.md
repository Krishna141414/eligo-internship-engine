# Web Interface Guidelines audit (Phase 7)

Audited on 2026-11-26 against the Vercel Web Interface Guidelines (`vercel-labs/web-interface-guidelines`, `command.md`, fetched the same day) over `templates/`, `static/css/theme.css` and `static/js/`. Every finding below is fixed, and each fix has a test in `tests/django/test_guidelines.py` (or the test named next to it).

## Findings and fixes

| Where | Finding | Fix |
|---|---|---|
| `templates/adminpanel/ml.html:51` | Figure images had no `width`/`height` (layout shift while loading) | Width and height read from each PNG header |
| `templates/partials/skill_picker.html:8` | Placeholder didn’t end with “…” or show an example | `e.g. machine learning…` |
| `templates/partials/messages.html:2` | Every message used `role="alert"`, including “Profile saved.” | Success/info messages are `role="status"`; errors and warnings stay `alert` |
| `accounts/forms.py:13` and the register form | Email inputs were spell-checked | `spellcheck="false"` |
| Register form | Name, email and mobile had no `autocomplete` token | `name`, `email`, `tel` (+ `inputmode="numeric"` for mobile); `test_register_fields_have_autocomplete_tokens` |
| Profile form | Non-auth fields had no `autocomplete` decision | `organization`, `address-level2`, and `off` for the rest |
| `templates/assessments/questions.html:19` | Deleting a question had no confirmation | `data-confirm` dialog before the POST |
| `templates/partials/form.html` + `static/js/ui.js` | The first invalid field wasn’t focused after a failed submit | Django marks it `aria-invalid="true"`; `ui.js` focuses it |
| Profile and admin forms | Leaving the page lost unsaved edits silently | `data-warn-unsaved` → `beforeunload` warning while the form is dirty |
| `static/css/theme.css` | The sticky top bar and exam bar could cover a focused element or an anchor target | `scroll-padding-top` on `html`, `scroll-margin-top` on exam questions |
| `static/css/theme.css` | No `touch-action: manipulation`, no intentional tap highlight, no `overscroll-behavior: contain` on the drawer and dialogs | Added |
| `static/css/theme.css` | Long chips and titles could overflow on phones | `overflow-wrap: anywhere` + `min-width: 0` |
| `static/css/theme.css` | Native `select` had no explicit background/colour; no `color-scheme` | Both set (light theme) |
| `templates/base.html` | Fonts weren’t preloaded; no `theme-color`; brand name could be machine-translated | Preload of the two above-the-fold faces, `theme-color` = page background, `translate="no"` on the wordmark |
| Templates (visible copy) | Straight quotes and apostrophes | Curly quotes in all visible text (`test_visible_copy_uses_curly_quotes`) |
| `/favicon.ico` | 404 on pages that don’t link an icon (Django’s debug 404 page) | Permanent redirect to the SVG icon; `test_favicon_ico_serves_the_svg_icon` |

## Rules checked and already met

Icon-only buttons have labels; decorative icons are `aria-hidden`; every input has a label; skip link and heading order; `:focus-visible` rings everywhere; no `transition: all`; only colour/shadow/transform transitions, all off under reduced motion; Chart.js and tooltips don’t animate; tabular numbers in number columns; `text-wrap: balance` on headings; loading states (“checking…”); filters and pagination live in the URL; real links for navigation; the submit button stays enabled until the request starts, then shows a spinner (`data-busy`); empty states on every list; zoom isn’t disabled.

## Not applied, with reasons

- **Title Case for headings and buttons:** the project’s copy rules (BUILD_PROMPT 5.6) require sentence case, and the spec wins.
- **`Intl.DateTimeFormat` / `Intl.NumberFormat`:** dates and numbers are formatted on the server by Django (`date`, `intcomma`), the same for every visitor; no JavaScript formats a date.
- **List virtualisation:** lists are paginated at 20 rows; the 188 career-skill checkboxes are static and cheap.
- **`preconnect`:** there are no CDN or third-party origins (everything is vendored, hard rule 19).
- **Dark mode:** the design is light-only by choice (CLAUDE.md palette); `color-scheme: light` stops browsers from half-darkening form controls.
- **Hydration rules:** there is no client-side framework.
- **The loading message** “Analysing your profile… checking 7,566 internships” keeps Krishna’s wording rather than ending on a second ellipsis.
