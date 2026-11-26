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

## Licence

MIT for the code. Datasets keep their own licences (see `docs/DATASETS.md`).
