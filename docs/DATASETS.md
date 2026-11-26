# Datasets — Eligo

Every dataset here is free, publicly downloadable and licensed for academic use. Nothing is fabricated.
Selection details and the rejected candidates are in `docs/DECISIONS.md` (D-005, D-006). Last updated: 2026-11-24 (Phase 1).

| Role | Dataset | Licence | Size | Synthetic? | Status |
|---|---|---|---|---|---|
| A. Job-role training | Student Career Dataset (Mendeley, v2) | CC BY 4.0 | 4,076 rows × 2 cols (2,176 after removing exact duplicates) | **No**, real student survey | ✅ downloaded to `data/raw/mendeley_student_career/`, SHA-256 verified |
| B. Internship listings | Internship Opportunities in India (2025) (Kaggle) | MIT (as declared by uploader) | 8,483 postings × 13 cols | **No**, scraped real Internshala postings | ✅ downloaded by Krishna (Kaggle login) to `data/raw/kaggle_internships_2025/`, profiled 2026-11-24 |

---

## A. Job-role training data — Student Career Dataset

| Field | Value |
|---|---|
| Name | Student Career Dataset, version 2 |
| Authors | Sakir Hossain Faruque, Sharun Akter Khushbu |
| URL | https://data.mendeley.com/datasets/4spj4mbpjr/2 (DOI 10.17632/4spj4mbpjr.2) |
| Published | 2024-10-17 |
| Licence | CC BY 4.0 (attribution required: cite the authors + DOI in README) |
| File | `Career Dataset.xlsx` (136,650 bytes, SHA-256 `df029f3b…26d901e5`, matches Mendeley's published hash) |
| Rows / columns | 4,076 × 2; **1,900 exact duplicate rows** → 2,176 unique rows |
| Synthetic? | **No.** Survey of Computer Science / Software Engineering students at public and private universities in Bangladesh (Google Forms, self-reported). |
| Collected by our profile form? | **Yes.** The only feature is the student's own skill list, which the profile collects directly. |

**Columns**

| Column | Type | Description | Used as |
|---|---|---|---|
| `Skill` | text (comma-separated list) | Skills the student reported, e.g. "Web Development, Mobile App Development, Problem Solving and Analysis". 1,597 distinct raw tokens before normalisation (typos and variants such as "ProblemSolving", "Deeplearning"). | **Feature.** Normalised through `ml_core.skills` (synonym map + vocabulary) into a multi-hot skill vector. |
| `Career` | categorical, 6 classes | Career field the student aims for. | **Label** (job-role category). |

**Class distribution after exact de-duplication (real counts):** Software Development and Engineering 567 · Development 470 · Artificial Intelligence 436 · Data Science 337 · Security 309 · User Experience (UX) and User Interface (UI) Design 57.

**Known limitations (stated in README and on the prediction page):**
- Skills are the only feature. The dataset has **no academic percentage, qualification or assessment score**, so the job-role model can't use them (see D-008). Academic fields are still collected and used by the eligibility gates.
- The labels "Development" and "Software Development and Engineering" overlap in meaning. They are kept exactly as published: relabelling would mean inventing labels.
- 19 of 2,025 distinct skill-sets appear with more than one label (label noise in the source).
- The UX/UI class is small (57 unique rows). Per-class metrics will show this honestly.
- Population: Bangladeshi CS/SE students. Results may not transfer to other disciplines.

**Selection check (real computation, `docs/DECISIONS.md` D-005):** 5-fold CV of a simple bag-of-skills logistic regression gave accuracy 0.895 / macro-F1 0.905, against a majority-class baseline of 0.261. That shows the features carry real signal. This was a dataset-selection check only; the project's actual models and metrics are produced in Phase 3.

---

## B. Internship listings — Internship Opportunities in India (2025)

| Field | Value |
|---|---|
| Name | Internship Opportunities in India (2025) |
| Uploader | Kaggle user `jayaantanaath` |
| URL | https://www.kaggle.com/datasets/jayaantanaath/internship-opportunities-in-india-2025 |
| Licence | MIT (declared on Kaggle) |
| Source | Internshala internship postings, scraped by the uploader in 2025 |
| Files | `merged_internships_dataset.csv` (2.62 MB, all postings + `internship_id`) plus 9 per-city files (Bangalore, Chennai, Delhi, Hyderabad, Jaipur, Kolkata, Mumbai, Pune, work-from-home) that are subsets of it |
| Rows / columns | **8,483** postings × 13 columns (the uploader's description says 8,485; the file has 8,483) |
| File used | `merged_internships_dataset.csv`, 2,622,937 bytes (matches Kaggle's listed size), SHA-256 `06a82ae6d264433c267b0821d1d53c34d7234d6814d356d3250c578ffec187a6` |
| Scrape window | `Date Time` 2025-09-21 14:37 → 2025-09-28 10:11 |
| Synthetic? | **No.** Real scraped postings. |

**Columns** (all stored as text, no null cells; placeholders such as "Not Available" / "Not Specified" / "Nothing" stand in for missing values)

| Column | Expected content | Used as |
|---|---|---|
| `internship_id` | row id | Primary key → `Internship.source_id` |
| `Date Time` | scrape / posting timestamp | metadata |
| `profile` | internship title / role, e.g. "Data Science" | `internship_title`, `job_role` |
| `company` | company name | `company_name` |
| `Location` | city or "Work From Home" | `location`, `work_mode` (derived: remote vs on-site) |
| `Start Date` | e.g. "Immediately" | eligibility text |
| `Stipend` | text, e.g. "₹ 10,000 /month" | `stipend` (parsed to a number + kept as text) |
| `Duration` | text, e.g. "3 Months" | `duration` |
| `Apply by Date` | deadline text | `application_deadline` (parsed; dataset-relative, see D-007) |
| `Offer` | job-offer / PPO info | eligibility text |
| `Education` | required education, when stated | `required_qualification` + `specialization` (derived by a documented rule, D-007) |
| `Skills` | required skills list | `required_skills` (normalised via `ml_core.skills`) |
| `Perks` | certificate, flexible hours, etc. | description text |

**Confirmed on load (real counts, 2026-11-24). Every one of these gets a documented cleaning rule in Phase 3:**

| Finding | Count | Planned handling |
|---|---|---|
| Exact duplicates / duplicates ignoring `internship_id` | 0 / 0 | none needed |
| Same `profile` + `company` + `Location` | 956 | keep: different ids and skills or stipends, so these look like separate openings; reviewed in EDA |
| `profile` = "Nothing" (no title; these 207 rows also have Location "Not Available") | 207 | drop: no title to match on |
| Scraper column shift: `Start Date` holds long free text (e.g. a company bio) | 69 | drop or flag the row |
| `Duration` isn't a duration (e.g. "1 week ago", posting age) | 60 | set duration to unknown, flag |
| `Skills` = "Not Available" | 213 | keep, but no skill-match score (component = 0, explained) |
| `Apply by Date` = "Not Available" | 1,260 | no deadline → deadline gate passes, flagged |
| `Stipend` = "Not Available" / "Unpaid" | 336 / 180 | parsed to `None` / 0 |
| `Offer` = "Nothing" on **every** row | 8,483 | column dropped (no information) |
| `Education` = "Not Specified" | 6,539 (77%) | → "Any Graduate" default (D-007) |
| `Education` specified | 1,944 | 1,139 mention a degree or qualification keyword → rule-parsed; 805 hold other text (221 are location limits such as "are from Mumbai only", others are duties) → "Any Graduate" + kept as eligibility note |
| `Skills` vocabulary | 793 distinct tokens, median 4 per posting | normalised via `ml_core.skills` |
| `Perks` vocabulary | 6 tokens (Certificate, Letter of Recommendation, Flexible, 5 Days A Week, Mentorship, Not Available) | description text |
| Domain mix | 1,977 distinct titles; top are Business Development (650), Digital Marketing (329), HR (324); about 1,716 are tech-related | see note below |

**Domain mismatch to handle:** the job-role model predicts 6 **CS career fields** (dataset A), but most internships are non-tech. "Related internships" on the prediction page therefore use a documented career-field → internship-title keyword map plus a semantic-similarity fallback, built in Phase 3. The main recommender isn't affected: it ranks by the student's own skills and profile against each posting.

**Known limitations:**
- **No full description column.** The text used for TF-IDF and semantic matching (`description`) is **composed** from `profile + Skills + Education + Perks + Offer`, cleaned (HTML, whitespace, boilerplate) and flagged with `description_derived = True`. Admin-added internships can have a real free-text description.
- `minimum_academic_percentage` is not in the data. It is set to a neutral 0% default that admins can edit, and flagged as derived (D-007).
- Postings are a 2025 snapshot (scraped 21–28 Sep 2025; deadlines mostly in Oct 2025). Deadlines are in the past relative to the demo date, so the "deadline not passed" gate compares against a configurable reference date (D-007; default 2025-09-28, the last scrape day).
- Scraped from Internshala and re-shared by the uploader under MIT. Eligo uses it only for non-commercial academic demonstration and credits both the uploader and Internshala as the original source.

**Why this one (summary of D-006):** it is the only free candidate found with **both required skills and required education** for thousands of real postings. The originally suggested "Internship Insights" (`aayush9119`) only has title, company, location, start date, duration, stipend, status and link, with no skills, education or description, so it can't support skill matching or the qualification gate.

---

## Rejected candidates (evidence-based)

| Dataset | Why rejected (real checks run on 2026-11-24) |
|---|---|
| Student Skill Gap Analysis, Mendeley `rv6scbpd7v` (CC BY 4.0, 500 rows) | Features look collectible, but there is **no detectable signal**: skills-text classifier CV accuracy 0.148 vs majority baseline 0.186; chi-square of course / year / projects / ratings vs role all p > 0.19. Value combinations look randomly generated. It also contains student names and emails. |
| CareerMap, Mendeley `5z68cvxssn` (CC BY 4.0, 9,179 rows) | Every role has exactly 540 rows (AI ML Specialist 1,080) and consecutive rows differ in a single column, which indicates augmentation. 10 of its 27 features are personality-test scores (Big Five / values) that our form can't collect without adding a psychometric questionnaire. |
| Career Path Prediction, Mendeley `cns7h4b9g7` (CC BY 4.0, 15,000 rows) | **Synthetic**: the label is a uniform random choice among 2–3 roles fixed by `Fields_of_Interest`, and all other columns are noise (e.g. "12th" + "Civil" stream, B.Sc + "BBA" stream). Random forest CV accuracy 0.317, about chance within the interest group. |
| Internship Insights, Kaggle `aayush9119/internshala-dataset` (Apache 2.0) | No skills, education or description columns. |
| Other Internshala scrapes on Kaggle (`himanshu9648`, `khushipitroda`, `pradeepkisku`, `ghosh153`, …) | Each lacks education and/or skills, or has an unclear licence. |
| AICTE Government Internship Dataset, Kaggle (MIT, ~2,000 rows) | No skills or education columns. |
| `logiover/internshala-scraper-sample-data`, Hugging Face (CC BY 4.0) | Has real descriptions but only 50 rows. |

The three rejected Mendeley files remain in `data/raw/` (git-ignored) so the checks above can be re-run.

## Demo / illustrative data

Demo student profiles and sample MCQs are created by `seed_demo` and labelled **DEMO** in the data, UI and README. They are never used as training data.

## Cleaning update (Phase 6.5, D-031)
Repeated listings (same title, company, location, stipend and skills) are kept once: 8,483 raw rows → 7,566 clean (207 without a title, 69 with shifted columns, 641 repeats). The listed start date is its own column (`start_date`) instead of part of the eligibility criteria.
