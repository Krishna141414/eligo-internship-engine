# End-to-end test run (Phase 6)

Run on 2026-11-26 with the Playwright MCP browser against `runserver` on the dev database (8,207 real internships, real artifacts verified by SHA-256, Ollama `qwen3:4b` running). Every step below asserted a condition in the page; the result column is what the assertion found. Screenshots are in `docs/e2e/`.

## 1. Viva demo script (README), after `reset_demo`

| Step | Check | Result |
|---|---|---|
| DEMO CS student logs in | Journey stepper's current step is "Assessment" | PASS |
| B.Tech/B.E. aptitude, 8 of 10 correct | Confirm dialog: "You've answered all 10 questions." | PASS |
| Submit | Result 80.00%, Qualified, 60% marker on the ring | PASS ([01](e2e/01-cs-result-80.png)) |
| Generate recommendations | 10 cards in 3.4 s; top 3 show "AI second opinion: checking…" | PASS ([02](e2e/02-cs-recommendations-pending.png)) |
| Wait on the same page | All three second opinions finished 6.3 s later, without a reload | PASS |
| Explain this match | XAI table with 3 score parts | PASS ([03](e2e/03-cs-explain-open.png)) |
| Open the full explanation | Page shows the eligibility checks | PASS ([04](e2e/04-cs-explanation-detail.png)) |
| Predict my job role | Artificial Intelligence, model confidence 95% | PASS ([05](e2e/05-cs-job-role.png)) |
| DEMO B.Sc student, Any Graduate aptitude, 6 of 10 correct | Result 60.00%, **Not qualified** (strictly above 60% needed) | PASS ([06](e2e/06-bsc-result-60-not-qualified.png)) |
| B.Sc student selects Generate | No cards; "Pass an assessment for your qualification with more than 60% to unlock recommendations." | PASS ([07](e2e/07-bsc-recommendations-locked.png)) |
| Admin dashboard | Outcomes: Qualified 1, Not qualified 1, Not attempted 1 | PASS ([08](e2e/08-admin-dashboard.png)) |
| Admin results / ML page | 2 result rows; both models listed | PASS |

## 2. New student, register to job role (BUILD_PROMPT Phase 6.2)

| Step | Check | Result |
|---|---|---|
| Register "DEMO – E2E check student" | Logged in, journey current step "Profile" | PASS ([10](e2e/10-register.png)) |
| Profile: B.Tech CSE, skills typed into the tag input, 3 career skills picked | 3 skill chips; the career-skill filter narrows the list; count shows 3 | PASS ([11](e2e/11-profile.png)) |
| Search internships "python" in Bangalore | 17 matches | PASS ([12](e2e/12-search.png)) |
| Start the 2-minute DEMO assessment | Exam HTML contains no answer data | PASS |
| 9 of 10 correct, submit | 90.00%, Qualified | PASS ([13](e2e/13-result-90.png)) |
| Recommendations, explanation, job role | 10 cards; explanation with 3 parts; Artificial Intelligence, 93% | PASS ([14](e2e/14-recommendations.png), [15](e2e/15-explanation.png), [16](e2e/16-job-role.png)) |
| Open another student's attempt URL | HTTP 404 | PASS |
| Retake, answer 1 of 10, submit | Confirm dialog: "9 unanswered questions will score 0." | PASS |
| Press Back after submitting | Lands on the result page, not a stale exam | PASS after fix (see below) |

## 3. Timer expiry (1-minute DEMO assessment)

| Case | Check | Result |
|---|---|---|
| Page open, 2 of 3 answered, no Submit | Pill starts red with "(under 1 minute)"; at 0:00 the page submits itself (~58 s); graded 66.67% on the two answers; recorded as Submitted (arrived within the 10 s grace) | PASS ([17](e2e/17-timer-critical.png), [18](e2e/18-timer-auto-submitted-result.png)) |
| 1 of 3 answered (autosave HTTP 200), student leaves, returns after 75 s | Server finalises the attempt: **Auto-submitted**, 33.33%, Not qualified, from the saved answer only; result page says "Submitted automatically when time ran out" | PASS ([19](e2e/19-auto-submitted-history.png), [20](e2e/20-auto-submitted-result.png)) |

## Bugs found by this run, and fixed

1. **Stale exam after Back.** After submitting, the browser's Back button showed the finished exam from its cache, timer and all, because the exam page sent no `Cache-Control` header. A second submit was already rejected as a duplicate, but the page looked live. Fix: `@never_cache` on the exam view, so Back always asks the server, which redirects to the result. Regression test: `test_exam_page_is_never_cached`. Re-run in the browser: PASS.
2. (Found by `test_concurrency.py`, not the browser.) Two simultaneous submits could raise "database is locked" instead of reporting a duplicate. Fix: SQLite `transaction_mode: IMMEDIATE` (D-027).

## Notes

- The first search tried ("machine learning" in Bangalore) returned 0 results. That's correct: the data has 19 machine-learning internships and none of them is in Bangalore. The run then used a query that exists.
- Console: besides the intended 404 from the isolation check, the browser requested `/favicon.ico` on Django's debug 404 page, and Chrome suggested `autocomplete` attributes on the register form. Both are listed for the Phase 7 polish pass.
- After the run, `reset_demo` put the DEMO accounts back to a clean state. The "DEMO – E2E check student" account stays in the local dev database.
