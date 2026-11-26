# Screenshots

Taken on 2026-11-26 after `python manage.py reset_demo`, by clicking the full flow in a fresh browser session against the real app (7,566 internships, the saved models, `qwen3:4b` running in Ollama). Desktop shots are 1440 px wide; mobile shots are 390 px. Everything shown is DEMO data.

| # | File | What it shows |
|---|---|---|
| 01 | [01-dashboard.png](01-dashboard.png) | Student dashboard with every journey step done, the stat band, top matches and the predicted job role |
| 02 | [02-profile.png](02-profile.png) | Profile form: free-text skills as chips, and the career skills the job-role model understands as removable chips above the list |
| 03 | [03-exam.png](03-exam.png) | Exam screen: “1:59 left” timer pill, one question per view, and the question grid (answered, not answered, current) |
| 04 | [04-result-qualified.png](04-result-qualified.png) | DEMO CS student scores 80.00% and qualifies; the ring marks the 60% pass line |
| 05 | [05-result-not-qualified.png](05-result-not-qualified.png) | DEMO B.Sc student scores exactly 60.00% and does not qualify (the rule is strictly above 60%) |
| 06 | [06-recommendations.png](06-recommendations.png) | Ranked recommendation cards: score ring, weighted breakdown bar, skills you have and skills to build, AI second opinion filled in |
| 07 | [07-recommendations-ai-check.png](07-recommendations-ai-check.png) | The same page the moment it loads: the ranking is ready and the top cards still say “AI second opinion: checking…” |
| 08 | [08-recommendation-detail.png](08-recommendation-detail.png) | Full explanation of the #1 match: score table (part score × weight), every eligibility check, matched and missing skills |
| 09 | [09-job-role.png](09-job-role.png) | Job-role prediction: Artificial Intelligence at 96% confidence, probability per career field, the skills that weigh most, related internships |
| 10 | [10-internship-detail.png](10-internship-detail.png) | Internship page with the student’s “Your eligibility” panel (every gate passed) |
| 11 | [11-admin-dashboard.png](11-admin-dashboard.png) | Admin dashboard: stat band, assessment outcomes (1 qualified, 1 not qualified, 1 not attempted), “Not enough data yet” for the chart after a single run, recent results |
| 12 | [12-admin-ml.png](12-admin-ml.png) | ML monitoring: Decision Tree vs Random Forest metrics, accuracy and macro-F1 chart, confusion matrices, feature importance and the other notebook figures |
| 13 | [13-mobile-dashboard.png](13-mobile-dashboard.png) | Student dashboard on a phone: vertical journey stepper, two-column stat band |
| 14 | [14-mobile-exam.png](14-mobile-exam.png) | Exam on a phone: question first, navigation and Submit, question grid below |
| 15 | [15-mobile-recommendations.png](15-mobile-recommendations.png) | Recommendations on a phone: the first card with its score ring |
