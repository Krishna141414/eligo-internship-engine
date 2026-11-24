# Requirements checklist — Eligo

Every bullet of `docs/PROJECT_SPEC.md` sections 1–19 (plus the final goal) maps to one row.
"Where implemented" lists the **planned** location until the row is built, then the actual file/feature.

**Status legend:** ⬜ not started · 🟨 in progress / partial · ✅ done (verified) · ❌ not done (reason given)

Last updated: 2026-11-24 (Phase 1)

---

## Part A — Jupyter Notebook

### 1. Dataset requirements
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 1.1 | Free public dataset: student qualifications, academic details, skills | `docs/DATASETS.md` A, `data/raw/mendeley_student_career/` | 🟨 Student Career (real, CC BY 4.0) gives skills. No real dataset with signal also had academic details (D-005); academic fields are collected by the profile and used by eligibility gates |
| 1.2 | Free public dataset: job roles and career-related attributes | `docs/DATASETS.md` A | ✅ Student Career `Career` label, 6 classes (downloaded, SHA-256 verified) |
| 1.3 | Free public dataset: internship opportunities, descriptions, qualifications, required skills | `docs/DATASETS.md` B, `data/raw/kaggle_internships_2025/` | ✅ Internship Opportunities in India (2025), 8,483 real postings with skills + education (D-006). No description column → composed from the posting's own fields + flagged (D-007) |
| 1.4 | Assessment-related features where supported by the dataset | `docs/DECISIONS.md` D-008 | ✅ Decided: not supported by the training data → assessment is an eligibility gate only (stated on the prediction page) |
| 1.5 | Provide dataset download URLs and column descriptions | `docs/DATASETS.md`, README | 🟨 DATASETS.md done; Kaggle column contents confirmed at load (Phase 3); README in Phase 7 |
| 1.6 | Do not fabricate training data, labels or evaluation results | Whole project | 🟨 Three synthetic / no-signal candidates rejected on real checks (DATASETS.md); labels kept as published |

### 2. Data preprocessing
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 2.1 | Load and analyse datasets | notebook §3.1 | ⬜ |
| 2.2 | Handle missing values and duplicates | `ml_core/preprocessing.py`, notebook §3.2 | ⬜ |
| 2.3 | Encode categorical variables | `ml_core/preprocessing.py` (ColumnTransformer) | ⬜ |
| 2.4 | Process academic and skill-related features | `ml_core/preprocessing.py`, `ml_core/skills.py` | ⬜ |
| 2.5 | Clean internship descriptions | `ml_core/preprocessing.py` | ⬜ |
| 2.6 | Prepare training and testing datasets | notebook §3.2 (stratified split) | ⬜ |
| 2.7 | Prevent data leakage | Dedup before split; Pipeline fitted on train only | ⬜ |

### 3. ML-based job role prediction
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 3.1 | Train Decision Tree Classifier | notebook §3.3, `artifacts/models/dt.joblib` | ⬜ |
| 3.2 | Train Random Forest Classifier | notebook §3.3, `artifacts/models/rf.joblib` | ⬜ |
| 3.3 | Predict job-role categories from academic info, skills, assessment features (where supported) | `ml_core/job_role.py` | ⬜ |
| 3.4 | Evaluate: Accuracy | `artifacts/metrics/metrics.json` | ⬜ |
| 3.5 | Evaluate: Precision | `artifacts/metrics/metrics.json` | ⬜ |
| 3.6 | Evaluate: Recall | `artifacts/metrics/metrics.json` | ⬜ |
| 3.7 | Evaluate: F1-score | `artifacts/metrics/metrics.json` | ⬜ |
| 3.8 | Evaluate: Confusion matrix | `artifacts/figures/`, metrics | ⬜ |
| 3.9 | Evaluate: Classification report | `artifacts/metrics/` | ⬜ |
| 3.10 | Select and save best-performing model | `artifacts/models/best_model.joblib`, `manifest.json` | ⬜ |

### 4. Hybrid AI internship recommendation engine
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 4.1 | Student profile and skill analysis | `ml_core/skills.py`, `ml_core/recommender.py` | ⬜ |
| 4.2 | Assessment eligibility check (score strictly above 60%) | `ml_core/eligibility.py` | ⬜ |
| 4.3 | Mandatory internship qualification check | `ml_core/eligibility.py` | ⬜ |
| 4.4 | Content-based filtering: TF-IDF + cosine similarity | `ml_core/recommender.py`, `artifacts/vectorizers/tfidf.joblib` | ⬜ |
| 4.5 | Semantic matching with Sentence Transformers | `ml_core/recommender.py`, `artifacts/models/sentence_model/` | ⬜ |
| 4.6 | Hybrid recommendation score calculation | `ml_core/recommender.py`, `artifacts/config/hybrid_config.json` | ⬜ |
| 4.7 | Ranking of eligible internships | `ml_core/recommender.py` | ⬜ |
| 4.8 | Matched and missing skill identification | `ml_core/skills.py`, `ml_core/recommender.py` | ⬜ |
| 4.9 | Use a lightweight Sentence Transformer (all-MiniLM-L6-v2) | `ml_core/config.py` | ⬜ |
| 4.10 | Use actual internship records and reusable Python functions | `artifacts/data/internships_clean.csv`, `ml_core/` | ⬜ |

### 5. LLM-based skill analysis
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 5.1 | Optional local LLM via Ollama (small instruct model) | `ml_core/llm_extract.py` | ⬜ PENDING – Ollama (install + model pull); model decided in Phase 1 |
| 5.2 | Extract student skills | `ml_core/llm_extract.py` | ⬜ |
| 5.3 | Extract internship-required skills | `ml_core/llm_extract.py` | ⬜ |
| 5.4 | Normalise skill names | `ml_core/skills.py`, `ml_core/llm_extract.py` | ⬜ |
| 5.5 | Compare student and internship requirements | `ml_core/llm_extract.py` | ⬜ |
| 5.6 | Identify skill gaps | `ml_core/llm_extract.py`, `ml_core/skills.py` | ⬜ |
| 5.7 | Validate structured outputs | `ml_core/llm_extract.py` (pydantic) | ⬜ |
| 5.8 | Rule-based fallback when LLM unavailable | `ml_core/skills.py`, `ml_core/llm_extract.py` | ⬜ |
| 5.9 | No RAG, no vector database | Whole project (banned list in CLAUDE.md) | ⬜ |

### 6. Explainable AI
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 6.1 | Explain qualification eligibility | `ml_core/explain.py` | ⬜ |
| 6.2 | Explain assessment eligibility | `ml_core/explain.py` | ⬜ |
| 6.3 | Show matched skills | `ml_core/explain.py` | ⬜ |
| 6.4 | Show missing skills | `ml_core/explain.py` | ⬜ |
| 6.5 | Show content and semantic similarity contributions | `ml_core/explain.py` | ⬜ |
| 6.6 | Show final internship match score | `ml_core/explain.py` | ⬜ |
| 6.7 | Explain actual recommendation factors only (no unsupported reasons) | `ml_core/explain.py` (templated from computed values) | ⬜ |
| 6.8 | Feature importance for job-role model | `ml_core/job_role.py`, `artifacts/figures/` | ⬜ |

### 7. Visualisation and model evaluation
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 7.1 | Dataset distribution charts | `artifacts/figures/` | ⬜ |
| 7.2 | Model accuracy and F1 comparison | `artifacts/figures/` | ⬜ |
| 7.3 | Confusion matrices | `artifacts/figures/` | ⬜ |
| 7.4 | Feature importance chart | `artifacts/figures/` | ⬜ |
| 7.5 | Internship similarity ranking chart | `artifacts/figures/` | ⬜ |
| 7.6 | Skill matching visualisation | `artifacts/figures/` | ⬜ |

### 8. Save models and artifacts
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 8.1 | Decision Tree model | `artifacts/models/dt.joblib` | ⬜ |
| 8.2 | Random Forest model | `artifacts/models/rf.joblib` | ⬜ |
| 8.3 | Best job-role prediction model | `artifacts/models/best_model.joblib` | ⬜ |
| 8.4 | Preprocessing pipeline and feature schema | `artifacts/models/preprocess.joblib`, `artifacts/config/feature_schema.json` | ⬜ |
| 8.5 | TF-IDF vectorizer | `artifacts/vectorizers/tfidf.joblib` | ⬜ |
| 8.6 | Sentence Transformer model or local reference | `artifacts/models/sentence_model/` | ⬜ |
| 8.7 | Hybrid recommendation configuration | `artifacts/config/hybrid_config.json` | ⬜ |
| 8.8 | Reusable recommendation functions | `ml_core/recommender.py` | ⬜ |
| 8.9 | LLM extraction configuration and fallback functions | `artifacts/config/llm_config.json`, `ml_core/llm_extract.py` | ⬜ |
| 8.10 | Model evaluation metrics | `artifacts/metrics/` | ⬜ |
| 8.11 | Visualisation images | `artifacts/figures/` | ⬜ |
| 8.12 | Cleaned internship dataset | `artifacts/data/internships_clean.csv` | ⬜ |
| 8.13 | Required model metadata | `artifacts/manifest.json` | ⬜ |
| 8.14 | Sample inference functions proving reload without retraining | notebook §3.7 reload test | ⬜ |
| 8.15 | **Deliverable:** complete executable notebook with all of the above | `notebooks/eligo_engine.ipynb` | ⬜ |

---

## Part B — Django web application

### 9. Technology stack
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 9.1 | Frontend: HTML5, CSS3, JavaScript, Bootstrap 5 | `templates/`, `static/`, `static/vendor/bootstrap/` | 🟨 Bootstrap 5.3.9 vendored |
| 9.2 | Backend: Django 5.2 LTS | `config/` | 🟨 Django 5.2.19 installed |
| 9.3 | Database: SQLite | `config/settings.py` | ⬜ |
| 9.4 | ML: scikit-learn, Joblib | `ml_core/` | 🟨 installed |
| 9.5 | AI recommendation: TF-IDF, Sentence Transformers, cosine similarity | `ml_core/recommender.py` | 🟨 libraries installed |
| 9.6 | LLM: optional Ollama | `ml_core/llm_extract.py` | ⬜ PENDING – Ollama |
| 9.7 | XAI: feature-based recommendation explanations | `ml_core/explain.py` | ⬜ |
| 9.8 | Visualisation: Chart.js | `static/vendor/chartjs/`, `static/js/charts.js` | 🟨 Chart.js 4.6.1 vendored |

### 10. Database tables
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 10.1 | Users (name, email, mobile, password hash, user_type, registered_date, status) | `accounts/models.py` | ⬜ |
| 10.2 | Student_Profiles | `students/models.py` | ⬜ |
| 10.3 | Internships | `internships/models.py` | ⬜ |
| 10.4 | Assessments | `assessments/models.py` | ⬜ |
| 10.5 | Assessment_Questions | `assessments/models.py` | ⬜ |
| 10.6 | Assessment_Attempts | `assessments/models.py` | ⬜ |
| 10.7 | Student_Answers | `assessments/models.py` | ⬜ |
| 10.8 | Internship_Recommendations | `recommendations/models.py` | ⬜ |
| 10.9 | Job_Role_Predictions | `recommendations/models.py` | ⬜ |
| 10.10 | Django authentication + secure password hashing | `accounts/` | ⬜ |
| 10.11 | Foreign keys, constraints, JSON fields, migrations | all apps' `models.py` + `migrations/` | ⬜ |

### 11. Admin module
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 11.1.1 | Admin login | `accounts/views.py` | ⬜ |
| 11.1.2 | Admin change password | `accounts/views.py` | ⬜ |
| 11.1.3 | Admin logout | `accounts/views.py` | ⬜ |
| 11.2.1 | Dashboard: total students | `adminpanel/views.py` | ⬜ |
| 11.2.2 | Dashboard: total internships | `adminpanel/views.py` | ⬜ |
| 11.2.3 | Dashboard: total assessments | `adminpanel/views.py` | ⬜ |
| 11.2.4 | Dashboard: qualified / not-qualified students | `adminpanel/views.py` | ⬜ |
| 11.2.5 | Dashboard: total recommendations | `adminpanel/views.py` | ⬜ |
| 11.3.1 | View registered students | `adminpanel/views.py` | ⬜ |
| 11.3.2 | View student academic profiles and skills | `adminpanel/views.py` | ⬜ |
| 11.3.3 | View student assessment results | `adminpanel/views.py` | ⬜ |
| 11.3.4 | View student internship recommendations | `adminpanel/views.py` | ⬜ |
| 11.3.5 | Activate / deactivate students | `adminpanel/views.py` | ⬜ |
| 11.4.1 | Add internship | `internships/views.py` (admin) | ⬜ |
| 11.4.2 | View internships | `internships/views.py` (admin) | ⬜ |
| 11.4.3 | Update internship | `internships/views.py` (admin) | ⬜ |
| 11.4.4 | Activate / deactivate internship | `internships/views.py` (admin) | ⬜ |
| 11.4.5 | Form fields: company, job role, qualification, skills, location, stipend, duration, eligibility criteria, deadline | `internships/forms.py` | ⬜ |
| 11.5.1 | Create qualification-based assessment | `assessments/views.py` (admin) | ⬜ |
| 11.5.2 | View / update / deactivate assessment | `assessments/views.py` (admin) | ⬜ |
| 11.5.3 | Add MCQ with four options and correct answer | `assessments/forms.py` | ⬜ |
| 11.5.4 | View / update / delete questions | `assessments/views.py` (admin) | ⬜ |
| 11.6.1 | View student assessment results | `adminpanel/views.py` | ⬜ |
| 11.6.2 | View obtained marks and percentage | `adminpanel/views.py` | ⬜ |
| 11.6.3 | View qualified / not-qualified status | `adminpanel/views.py` | ⬜ |
| 11.7.1 | View student-wise recommended internships | `adminpanel/views.py` | ⬜ |
| 11.7.2 | View match scores and ranking | `adminpanel/views.py` | ⬜ |
| 11.7.3 | View recommendation explanations | `adminpanel/views.py` | ⬜ |
| 11.7.4 | View matched and missing skills | `adminpanel/views.py` | ⬜ |
| 11.8.1 | View student job-role predictions | `adminpanel/views.py` | ⬜ |
| 11.8.2 | View saved ML model evaluation results | `adminpanel/views.py` (reads `artifacts/metrics/`, `artifacts/figures/`) | ⬜ |

### 12. Student module
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 12.1.1 | Student registration | `accounts/views.py` | ⬜ |
| 12.1.2 | Login | `accounts/views.py` | ⬜ |
| 12.1.3 | Update profile | `students/views.py` | ⬜ |
| 12.1.4 | Change password | `accounts/views.py` | ⬜ |
| 12.1.5 | Logout | `accounts/views.py` | ⬜ |
| 12.2.1 | Update qualification and specialisation | `students/forms.py` | ⬜ |
| 12.2.2 | Update college and academic percentage | `students/forms.py` | ⬜ |
| 12.2.3 | Add / update skills | `students/forms.py`, skill tag input JS | ⬜ |
| 12.2.4 | Select career interests | `students/forms.py` | ⬜ |
| 12.2.5 | Select preferred job role and location | `students/forms.py` | ⬜ |
| 12.3.1 | Dashboard: available internships | `students/views.py` | ⬜ |
| 12.3.2 | Dashboard: available assessments | `students/views.py` | ⬜ |
| 12.3.3 | Dashboard: latest assessment result | `students/views.py` | ⬜ |
| 12.3.4 | Dashboard: recommended internships | `students/views.py` | ⬜ |
| 12.3.5 | Dashboard: predicted job role | `students/views.py` | ⬜ |
| 12.4.1 | View active internships | `internships/views.py` | ⬜ |
| 12.4.2 | Search by qualification, job role, location | `internships/views.py` | ⬜ |
| 12.4.3 | View internship details and eligibility criteria | `internships/views.py` | ⬜ |
| 12.5.1 | View qualification-based assessments | `assessments/views.py` | ⬜ |
| 12.5.2 | Select and start assessment | `assessments/views.py` | ⬜ |
| 12.5.3 | Attempt MCQ questions | `assessments/views.py`, exam template | ⬜ |
| 12.5.4 | View remaining time | `static/js/timer.js` (server-provided remaining seconds) | ⬜ |
| 12.5.5 | Submit assessment | `assessments/views.py` | ⬜ |
| 12.5.6 | Auto-submit when time expires | `static/js/timer.js` + server-side lazy finalisation | ⬜ |
| 12.6.1 | Result: total questions | result template | ⬜ |
| 12.6.2 | Result: correct answers | result template | ⬜ |
| 12.6.3 | Result: obtained marks | result template | ⬜ |
| 12.6.4 | Result: assessment percentage, `(obtained / total) × 100` | `assessments/services.py` (Decimal) | ⬜ |
| 12.6.5 | Result: qualified / not-qualified status | `assessments/services.py` | ⬜ |
| 12.7.1 | Check assessment and qualification eligibility | `recommendations/services.py` → `ml_core/eligibility.py` | ⬜ |
| 12.7.2 | Analyse student skills and academic profile | `recommendations/services.py` | ⬜ |
| 12.7.3 | Match student profile with internship requirements | `recommendations/services.py` → `ml_core/recommender.py` | ⬜ |
| 12.7.4 | Generate hybrid AI-based recommendations | `recommendations/services.py` | ⬜ |
| 12.7.5 | View ranked internships with match scores | recommendations template | ⬜ |
| 12.7.6 | View matched and missing skills | recommendations template | ⬜ |
| 12.7.7 | View XAI recommendation reasons | recommendations template | ⬜ |
| 12.8.1 | Predict job role from academic profile + available assessment features | `recommendations/services.py` → `ml_core/job_role.py` | ⬜ |
| 12.8.2 | View predicted job role | job-role template | ⬜ |
| 12.8.3 | View related internship opportunities | job-role template | ⬜ |

### 13. Django AI model integration
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 13.1 | Load trained job-role model with Joblib | `ml_core/artifacts.py` | ⬜ |
| 13.2 | Load fitted preprocessing pipeline and feature schema | `ml_core/artifacts.py` | ⬜ |
| 13.3 | Load saved TF-IDF vectorizer | `ml_core/artifacts.py` | ⬜ |
| 13.4 | Load Sentence Transformer model | `ml_core/artifacts.py` | ⬜ |
| 13.5 | Import reusable hybrid recommendation functions | `recommendations/services.py` imports `ml_core` | ⬜ |
| 13.6 | Mandatory eligibility checks | `ml_core/eligibility.py` | ⬜ |
| 13.7 | Similarity scores and ranked results | `ml_core/recommender.py` | ⬜ |
| 13.8 | Optional LLM skill extraction integrated | `recommendations/services.py` | ⬜ |
| 13.9 | Explainable recommendations | `ml_core/explain.py` | ⬜ |
| 13.10 | Save predictions and recommendations to SQLite | `recommendations/services.py` | ⬜ |
| 13.11 | Do not retrain models inside Django | Code review + test | ⬜ |
| 13.12 | Use same preprocessing and recommendation configs as notebook | shared `ml_core/` + `artifacts/config/` | ⬜ |

### 14. End-to-end processing rules
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 14.1 | Student registers and completes academic profile | `accounts/`, `students/` | ⬜ |
| 14.2 | Student searches available internships | `internships/` | ⬜ |
| 14.3 | Student attempts qualification-based assessment | `assessments/` | ⬜ |
| 14.4 | System automatically evaluates assessment | `assessments/services.py` | ⬜ |
| 14.5 | Score strictly above 60% satisfies assessment eligibility | `assessments/services.py`, `ml_core/eligibility.py` | ⬜ |
| 14.6 | Check mandatory qualifications and other explicit eligibility rules | `ml_core/eligibility.py` | ⬜ |
| 14.7 | Hybrid engine ranks only eligible internships | `ml_core/recommender.py` | ⬜ |
| 14.8 | Display scores, matched skills, missing skills, explanations | recommendations template | ⬜ |
| 14.9 | ML model predicts job-role category separately | `ml_core/job_role.py` | ⬜ |
| 14.10 | All important results stored in the database | `recommendations/services.py`, `assessments/services.py` | ⬜ |
| 14.11 | Mandatory qualifications/thresholds never overridden by similarity scores | `ml_core/eligibility.py` gates run before scoring | ⬜ |

### 15. User interface requirements
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 15.1 | Attractive academic and career-themed design | `static/css/theme.css`, templates | ⬜ |
| 15.2 | Responsive Bootstrap layouts | templates | ⬜ |
| 15.3 | Separate admin and student dashboards | `adminpanel/`, `students/` | ⬜ |
| 15.4 | Simple forms and navigation | templates | ⬜ |
| 15.5 | Searchable internship listings | `internships/` | ⬜ |
| 15.6 | Online MCQ interface with timer | exam template, `static/js/timer.js` | ⬜ |
| 15.7 | Recommendation cards with match scores | recommendation card partial | ⬜ |
| 15.8 | Matched and missing skills visualisation | skill chips + chart | ⬜ |
| 15.9 | Job-role prediction result page | job-role template | ⬜ |
| 15.10 | User-friendly validation and error messages | forms + templates | ⬜ |
| 15.11 | Avoid unnecessary animations, complex dashboards, decorative elements | `theme.css` motion rules | ⬜ |

### 16. Security and validation
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 16.1 | Django built-in authentication | `accounts/` | ⬜ |
| 16.2 | Store passwords securely | Django hashers | ⬜ |
| 16.3 | Protect admin and student routes | role decorators/mixins | ⬜ |
| 16.4 | Validate student profiles and assessment inputs | forms + validators | ⬜ |
| 16.5 | Prevent duplicate assessment submissions | `transaction.atomic` + `select_for_update` | ⬜ |
| 16.6 | Enforce assessment timing on the server | `assessments/services.py` (deadline) | ⬜ |
| 16.7 | Don't expose correct answers during exams | exam view excludes `correct_option` | ⬜ |
| 16.8 | Restrict students to their own results | ownership checks (404) | ⬜ |
| 16.9 | Load ML models only from trusted local files | `ml_core/artifacts.py` + `manifest.json` SHA-256 | ⬜ |
| 16.10 | Handle missing model artifacts gracefully | `ml_core/artifacts.py`, banner in UI | ⬜ |
| 16.11 | Preserve historical assessment scores | no delete/overwrite of attempts | ⬜ |

### 17. Software requirements
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 17.1 | Python 3.12 | `.venv` | ✅ 3.12.10 (Phase 0) |
| 17.2 | JupyterLab | `.venv` | ✅ 4.6.6, kernel "Python (Eligo)" registered |
| 17.3 | Visual Studio Code | Krishna's machine | ✅ in use |
| 17.4 | Django 5.2 LTS | `.venv` | ✅ 5.2.19 |
| 17.5 | SQLite | bundled with Python | ✅ |
| 17.6 | Chrome / Edge | Krishna's machine; Playwright for tests | ✅ Edge ships with Windows 11 |
| 17.7 | numpy, pandas, scikit-learn, scipy, joblib, matplotlib, seaborn, sentence-transformers, torch, django, openpyxl | `requirements.txt` | ✅ installed + pinned |
| 17.8 | Optional: Ollama + small local LLM | system install | ⬜ PENDING – Ollama (installer downloading); model decided in Phase 1 |
| 17.9 | Optional: pydantic | `requirements.txt` | ✅ 2.14.4 |
| 17.10 | Optional: shap | `requirements.txt` | ✅ 0.54.1 |
| 17.11 | No RAG, LangChain, ChromaDB, FAISS, cloud deploy, paid APIs | `requirements.txt` has none | ✅ (re-checked each phase) |

### 18. Testing requirements
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 18.1 | Student registration and login | `tests/` | ⬜ |
| 18.2 | Admin internship management | `tests/` | ⬜ |
| 18.3 | Qualification-based assessment | `tests/` | ⬜ |
| 18.4 | Automatic assessment evaluation | `tests/` | ⬜ |
| 18.5 | Score above 60% eligibility (boundary: 60.00 → Not_Qualified) | `tests/` | ⬜ |
| 18.6 | Qualification eligibility checking | `tests/test_ml_core_eligibility.py` | ⬜ |
| 18.7 | Content-based internship matching | `tests/test_ml_core_recommender.py` | ⬜ |
| 18.8 | Semantic similarity matching | `tests/test_ml_core_recommender.py` | ⬜ |
| 18.9 | Hybrid recommendation ranking | `tests/test_ml_core_recommender.py` | ⬜ |
| 18.10 | Matched skills and skill-gap explanation | `tests/test_ml_core_explain.py` | ⬜ |
| 18.11 | Job-role prediction | `tests/test_ml_core_job_role.py` | ⬜ |
| 18.12 | Saved model integration | `tests/` | ⬜ |
| 18.13 | Missing model and invalid input handling | `tests/` | ⬜ |
| 18.14 | Actual data for evaluation; illustrative test profiles clearly labelled, never presented as training data | DEMO labels in data/UI/README | ⬜ |

### 19. Final development instructions
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 19.1 | Complete executable notebook and Django source code | `notebooks/`, Django apps | ⬜ |
| 19.2 | Complete notebook before Django integration | phase order (3 before 4) | ⬜ |
| 19.3 | Only freely available datasets and pretrained models | `docs/DATASETS.md` | ⬜ |
| 19.4 | Two user roles: Admin and Student | `accounts/models.py` | ⬜ |
| 19.5 | Every essential functional requirement implemented | this checklist | ⬜ |
| 19.6 | Reusable Python functions for recommendations and inference | `ml_core/` | ⬜ |
| 19.7 | No retraining in Django | `ml_core/artifacts.py` (load only) | ⬜ |
| 19.8 | No fabricated datasets, performance or predictions | whole project | ⬜ |
| 19.9 | Consistent model input features between training and inference | `feature_schema.json` | ⬜ |
| 19.10 | Deterministic fallback when LLM unavailable | `ml_core/llm_extract.py` | ⬜ |
| 19.11 | Django migrations, requirements.txt, README | repo root | 🟨 requirements.txt done |
| 19.12 | Windows-compatible local demonstration | README, offline vendored assets | 🟨 assets vendored, no CDN |
| 19.13 | No integration with official government portal | scope | ⬜ |
| 19.14 | No internship allocation, payments, or employer recruitment modules | scope | ⬜ |
| 19.15 | All required buttons, pages, forms and features functional | Playwright E2E (Phase 6) | ⬜ |

### Final project goal
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| G.1 | Flow: Profile → Assessment → Evaluation → Eligibility → Hybrid recommendation → Explanations → Job-role prediction | end-to-end app | ⬜ |
| G.2 | Demonstrates qualification-aware recommendation, content + semantic matching, optional LLM, XAI, supervised job-role prediction | whole project | ⬜ |
| G.3 | Independent academic prototype, no claim of official allocation or integration (disclaimer) | footer + README | ⬜ |

---

## Phase exit checks

### Phase 0 — Setup
- [x] venv works: `python -c "import django, sklearn, sentence_transformers; print('ok')"`
- [x] Skills listed (Hallmark, web-design-guidelines, Humanizer, Django skills, scikit-learn) + MCPs (Playwright, Context7) + plugins (Superpowers, Last30days, Diagram Design)
- [x] Vendor files present in `static/vendor/`
- [x] This checklist file created
- [ ] **Step 8 (Ollama install): PENDING – Ollama.** The winget install was stopped on 2026-11-22. On 2026-11-24 a resumable `curl.exe -L -C -` download of `OllamaSetup.exe` to `%USERPROFILE%\Downloads\` was started in the background. When it finishes: run the installer (Krishna clicks Yes), then verify with `ollama --version`.
- [x] Step 11: session restarted, new skills loaded (2026-11-24)

### Phase 1 — Research and decisions
- [x] Last30days on all 4 topics + web supplements → `docs/RESEARCH.md` (2026-11-24; thin 30-day signal stated honestly)
- [x] Context7 docs: Django 5.2, sentence-transformers, scikit-learn 1.9, Chart.js 4, Bootstrap 5.3, Ollama `/api/chat` → `docs/RESEARCH.md` §5
- [x] DATASETS.md complete: name, URL, licence, rows/cols, column descriptions, synthetic yes/no, why chosen, rejected candidates
- [x] Raw data present in `data/raw/`: Student Career (SHA-256 verified against Mendeley) + Kaggle `merged_internships_dataset.csv` (8,483 × 13, size matches Kaggle, profiled 2026-11-24)
- [x] All decisions logged: D-005 datasets A, D-006 dataset B, D-007 qualification fields, D-008 assessment feature, D-009 Ollama model, D-010 UI kit, D-011 SQLite locking
- [ ] Step 6 `ollama pull qwen3:4b`: PENDING – Ollama (needs install first, then Krishna's approval)

### Phase 2 — Plan
- [x] Brainstorming → design `docs/superpowers/specs/2026-11-24-eligo-design.md` (approaches + decisions D-012…D-019)
- [x] writing-plans → `docs/PLAN.md`: 23 tasks for Phases 3–7, file list, data flow (notebook → artifacts → `ml_core.artifacts` → Django services → SQLite; `load_internships`; saved TF-IDF + sentence model for admin-added internships with the D-014 cache), typed `ml_core` public API, test plan mapped to every spec §18 scenario
- [x] Self-review: spec coverage, type consistency, Review Focus tests placed in their owning tasks

## PENDING – Ollama (tracker)
Items that need a live Ollama. Everything else goes ahead without it, because the project never depends on Ollama and the rule-based fallback always works.

| Item | What waits | Status |
|---|---|---|
| Phase 0 step 8 | Install Ollama + `ollama --version` | PENDING – Ollama (installer downloading) |
| Phase 1 step 6 | `ollama pull qwen3:4b` (~2.5 GB; DECIDED in D-009; pulled only after Krishna approves) | PENDING – Ollama |
| Phase 3.5 | Live LLM test of `ml_core/llm_extract.py` (the code + rule-based fallback get built in full in Phase 3; only the live run waits) | PENDING – Ollama |
