# Eligo

Eligibility-first, explainable internship matching.

Eligo takes a student profile, runs a qualification-based MCQ assessment, checks eligibility (score strictly above 60% plus the required qualification), and ranks only the internships the student can actually apply to. Ranking is a hybrid of TF-IDF similarity, sentence-transformer similarity and skill overlap, and every score comes with its breakdown. A separate model predicts a likely job role from the student's skills.

Django + scikit-learn, runs fully offline on a Windows laptop.

> Independent academic prototype, not affiliated with the official PM Internship Scheme portal.

*This README is a working draft. Phase 7 adds the architecture diagram, datasets and licences, model results and screenshots.*

## Setup (Windows, PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\setup_sentence_model.py   # one-time download of all-MiniLM-L6-v2, verified by SHA-256
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py load_internships
.\.venv\Scripts\python.exe manage.py seed_demo                # DEMO students and DEMO assessments
.\.venv\Scripts\python.exe manage.py create_admin
```

The sentence-model step is the only one that needs internet. After it, everything runs offline.

## Demo checklist

1. **Optional: start Ollama** with the `qwen3:4b` model (`ollama list` should show it). Eligo never depends on it. Without Ollama, the rule-based skill check runs and the page says so.
2. **Warm the local LLM** so the first AI second opinion isn't slow:
   ```powershell
   .\.venv\Scripts\python.exe manage.py warm_llm
   ```
   It loads the model into memory and keeps it warm for 30 minutes (`--keep-alive 1h` to change that). `runserver` also starts a non-blocking warm-up in the background; set `ELIGO_WARM_LLM=0` to turn that off.
3. **Start the server:** `.\.venv\Scripts\python.exe manage.py runserver`, then open http://127.0.0.1:8000/.
4. **Student flow:** log in as a DEMO student (accounts and the DEMO password are printed by `seed_demo`), take the assessment for the profile's qualification, then select "Generate recommendations". The ranked cards appear in about 3 seconds. The top 3 cards then show "AI second opinion: checking…" while the local model cross-checks them, one at a time; the page never waits for it.
5. **Job role:** open "Job role" and select "Predict my job role". It uses only the career skills picked in the profile.
6. **Admin:** log in with the admin account to see the dashboard, results, recommendation runs and the ML monitoring page.

All DEMO accounts, profiles and assessments are illustrative and labelled DEMO. They are not training data.

## Viva demo script (about 5 minutes)

**Before the viva** (once, with an admin account already made by `create_admin`):

```powershell
.\.venv\Scripts\python.exe manage.py reset_demo     # DEMO students back to a clean state; never touches other data
.\.venv\Scripts\python.exe manage.py warm_llm       # optional: loads qwen3:4b so the AI second opinion is quick
.\.venv\Scripts\python.exe manage.py runserver
```

DEMO password for every DEMO student: `Eligo-DEMO-2026!` (or `ELIGO_DEMO_PASSWORD` if you set it). The DEMO assessments are 2 minutes long, so answer briskly. The answer keys below come from the illustrative DEMO questions in `recommendations/management/commands/seed_demo.py`; the exam page itself never sends answers to the browser.

**1. CS student qualifies at 80% (about 2 minutes)**
1. Log in as `demo.cs@eligo.local`. The dashboard shows the journey stepper at "Assessment".
2. Assessments → "DEMO – B.Tech/B.E. aptitude" → Start assessment.
3. Answer questions 1–8 correctly (B, B, B, C, B, D, B, C) and questions 9–10 with A. Point out the timer pill and the question palette.
4. Submit assessment → the confirm dialog shows 0 unanswered → Submit now. Result: **80.00%, Qualified**, with the 60% marker on the ring.

**2. Recommendations and the explanation (about 1.5 minutes)**
1. Continue to recommendations → Generate recommendations. "Analysing your profile… checking 8,207 internships" shows while it ranks (about 3 seconds).
2. Ten ranked cards appear. Only eligible internships are ranked. The top 3 say "AI second opinion: checking…" and fill in a few seconds later without reloading. Without Ollama they say the second opinion isn't available and the rule-based check stands.
3. On card #1 open "Explain this match": part scores × weights = the final score, plus every eligibility check. Click the title for the full explanation page.

**3. Job role (about 30 seconds)**
- Job role → Predict my job role. The DEMO CS profile is predicted as Artificial Intelligence with high confidence (95% on the current model), with the probability chart and the skills that weigh most.

**4. B.Sc student at exactly 60% is not qualified (about 1 minute)**
1. Log out, then log in as `demo.bsc@eligo.local`.
2. Assessments → "DEMO – Any Graduate aptitude" → Start assessment.
3. Answer questions 1–6 correctly (C, C, B, B, B, C) and questions 7–10 with A, then submit.
4. Result: **60.00%, Not qualified**, because Eligo needs a score strictly above 60%. Recommendations stay locked for this student.

**5. Admin dashboard (about 30 seconds)**
- Log out, log in with the admin account. The dashboard shows the stat band, the outcome bar (1 qualified, 1 not qualified, 1 not attempted) and the most recommended internships. Results lists both attempts; ML models shows the Decision Tree vs Random Forest metrics and the notebook figures.

**Optional:** the "DEMO – 1-minute timer check" assessment, left alone, submits itself when the timer runs out, and the server records it.

Run `reset_demo` again after a rehearsal so the viva starts clean.

## Licence

MIT for the code. Datasets keep their own licences (see `docs/DATASETS.md`).
