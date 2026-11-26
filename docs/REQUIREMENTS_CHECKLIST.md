# Requirements checklist — Eligo

Every bullet of `docs/PROJECT_SPEC.md` sections 1–19 (plus the final goal) maps to one row.
"Where implemented" lists the **planned** location until the row is built, then the actual file/feature.

**Status legend:** ⬜ not started · 🟨 in progress / partial · ✅ done (verified) · ❌ not done (reason given)

Last updated: 2026-11-25 (Phase 4)

---

## Part A — Jupyter Notebook

### 1. Dataset requirements
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 1.1 | Free public dataset: student qualifications, academic details, skills | `docs/DATASETS.md` A, notebook §3.1 | ✅ Student Career (real survey, CC BY 4.0): skills → career. No real dataset with signal had academic details too (D-005); academic fields are collected by the profile and used by the gates |
| 1.2 | Free public dataset: job roles and career-related attributes | `docs/DATASETS.md` A | ✅ Student Career `Career` label, 6 classes (downloaded, SHA-256 verified) |
| 1.3 | Free public dataset: internship opportunities, descriptions, qualifications, required skills | `docs/DATASETS.md` B, `data/raw/kaggle_internships_2025/` | ✅ Internship Opportunities in India (2025), 8,483 real postings with skills + education (D-006). No description column → composed from the posting's own fields + flagged (D-007) |
| 1.4 | Assessment-related features where supported by the dataset | `docs/DECISIONS.md` D-008 | ✅ Decided: not supported by the training data → assessment is an eligibility gate only (stated on the prediction page) |
| 1.5 | Provide dataset download URLs and column descriptions | `docs/DATASETS.md`, README | 🟨 DATASETS.md done; Kaggle column contents confirmed at load (Phase 3); README in Phase 7 |
| 1.6 | Do not fabricate training data, labels or evaluation results | Whole project; DATASETS.md rejected list | ✅ for Part A: 3 synthetic/no-signal candidates rejected on real checks; labels kept as published; every metric printed by the notebook run |

### 2. Data preprocessing
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 2.1 | Load and analyse datasets | `notebooks/eligo_engine.ipynb` §3.1 | ✅ shapes, dtypes, heads, nulls, duplicates, placeholders, class distribution |
| 2.2 | Handle missing values and duplicates | `ml_core/preprocessing.py`, notebook §3.1–3.2 | ✅ 1,900 exact duplicates removed, then post-normalisation duplicates; placeholders → missing; tests `test_ml_core_preprocessing.py` |
| 2.3 | Encode categorical variables | `ml_core/skills.py` `SkillBinarizer` (inside the Pipeline) | ✅ multi-hot canonical skills (D-012); the target is the categorical label |
| 2.4 | Process academic and skill-related features | `ml_core/skills.py`, `ml_core/preprocessing.py` | ✅ canonical vocabulary 934 skills + synonym/compound map incl. survey spelling variants (D-022); model features 215; academic fields → gates |
| 2.5 | Clean internship descriptions | `ml_core/preprocessing.py` `clean_text`, `clean_internships` | ✅ HTML/whitespace/placeholders removed; composed description flagged `description_derived` |
| 2.6 | Prepare training and testing datasets | `notebooks/eligo_engine.ipynb` §3.2 | ✅ stratified 80/20, random_state 42: train 1,316 / test 330 (after D-022) |
| 2.7 | Prevent data leakage | dedup before split; `SkillBinarizer` vocabulary fitted on train folds only | ✅ test `test_binarizer_vocab_from_train_only`; notebook prints overlap check |

### 3. ML-based job role prediction
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 3.1 | Train Decision Tree Classifier | `artifacts/models/dt.joblib` | ✅ GridSearchCV (5-fold, macro-F1); test acc 0.8030, macro-F1 0.8048 (after D-022 vocabulary clean-up; test n=330) |
| 3.2 | Train Random Forest Classifier | `artifacts/models/rf.joblib` | ✅ GridSearchCV; test acc 0.8485, macro-F1 0.8787 (after D-022; best model) |
| 3.3 | Predict job-role categories from academic info, skills, assessment features (where supported) | `ml_core/job_role.py` `predict_job_role` | ✅ skills only (assessment not supported by the data, D-008); confidence + scope (D-021) |
| 3.4 | Evaluate: Accuracy | `artifacts/metrics/metrics.json` | ✅ |
| 3.5 | Evaluate: Precision | `artifacts/metrics/metrics.json` | ✅ macro + weighted |
| 3.6 | Evaluate: Recall | `artifacts/metrics/metrics.json` | ✅ macro + weighted |
| 3.7 | Evaluate: F1-score | `artifacts/metrics/metrics.json` | ✅ macro + weighted |
| 3.8 | Evaluate: Confusion matrix | `artifacts/figures/confusion_matrix_{dt,rf}.png`, metrics.json | ✅ |
| 3.9 | Evaluate: Classification report | `artifacts/metrics/classification_report_{dt,rf}.txt` | ✅ |
| 3.10 | Select and save best-performing model | `artifacts/models/best_model.joblib`, manifest.json | ✅ Random Forest (highest test macro-F1) |

### 4. Hybrid AI internship recommendation engine
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 4.1 | Student profile and skill analysis | `ml_core/skills.py`, `ml_core/preprocessing.py` `build_student_text` | ✅ |
| 4.2 | Assessment eligibility check (score strictly above 60%) | `ml_core/eligibility.py` `check_assessment`/`is_qualified` | ✅ boundary tests: 60.00 → Not_Qualified, 60.01/60.004 → Qualified |
| 4.3 | Mandatory internship qualification check | `ml_core/eligibility.py` `check_qualification` (D-017 hierarchy) | ✅ |
| 4.4 | Content-based filtering: TF-IDF + cosine similarity | `ml_core/recommender.py` `content_similarity`, `artifacts/vectorizers/tfidf.joblib` | ✅ fitted on 8,207 internships in the notebook; transform-only afterwards (tested) |
| 4.5 | Semantic matching with Sentence Transformers | `ml_core/recommender.py` `semantic_similarity`, `artifacts/embeddings/internships.npy` | ✅ all-MiniLM-L6-v2, pinned revision, cosine clipped to [0,1] |
| 4.6 | Hybrid recommendation score calculation | `ml_core/recommender.py` `hybrid_score`, `artifacts/config/hybrid_config.json` | ✅ 0.35 / 0.40 / 0.25 + sensitivity table on DEMO profiles |
| 4.7 | Ranking of eligible internships | `ml_core/recommender.py` `recommend` | ✅ gates first, ineligible never ranked (mutation-checked test) |
| 4.8 | Matched and missing skill identification | `ml_core/skills.py` `compare_skills` | ✅ |
| 4.9 | Use a lightweight Sentence Transformer (all-MiniLM-L6-v2) | `ml_core/config.py` `SENTENCE_MODEL_NAME/REVISION` | ✅ |
| 4.10 | Use actual internship records and reusable Python functions | `artifacts/data/internships_clean.csv` (8,207 real postings), `ml_core/` | ✅ |

### 5. LLM-based skill analysis
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 5.1 | Optional local LLM via Ollama (small instruct model) | `ml_core/llm_extract.py`, Ollama 0.40.18 + `qwen3:4b` | ✅ live: `tests/test_ml_core_llm_live.py` passes (2026-11-25) |
| 5.2 | Extract student skills | `ml_core/llm_extract.py` `extract_skills` | ✅ live LLM + fallback |
| 5.3 | Extract internship-required skills | `ml_core/llm_extract.py` `extract_skills` / `analyse_gap` | ✅ live LLM + fallback |
| 5.4 | Normalise skill names | `ml_core/skills.py` + `normalise_skills` on LLM output | ✅ |
| 5.5 | Compare student and internship requirements | `ml_core/llm_extract.py` `analyse_gap` | ✅ (rule-based path live; LLM path tested with a mocked Ollama response) |
| 5.6 | Identify skill gaps | `ml_core/llm_extract.py` `analyse_gap` | ✅ |
| 5.7 | Validate structured outputs | `ml_core/llm_extract.py` pydantic `SkillList` + JSON-schema `format` | ✅ retry once, then fallback (tested) |
| 5.8 | Rule-based fallback when LLM unavailable | `ml_core/skills.py` `extract_skills_rule_based` | ✅ deterministic, always available; `method` field on every result |
| 5.9 | No RAG, no vector database | whole project | ✅ no RAG / vector DB; one schema-constrained prompt |

### 6. Explainable AI
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 6.1 | Explain qualification eligibility | `ml_core/explain.py` (gates block) | ✅ |
| 6.2 | Explain assessment eligibility | `ml_core/explain.py` (assessment block vs 60%) | ✅ |
| 6.3 | Show matched skills | `ml_core/explain.py` | ✅ |
| 6.4 | Show missing skills | `ml_core/explain.py` | ✅ |
| 6.5 | Show content and semantic similarity contributions | `ml_core/explain.py` components (score × weight = contribution) | ✅ sums to the final score (tested) |
| 6.6 | Show final internship match score | `ml_core/explain.py` | ✅ |
| 6.7 | Explain actual recommendation factors only (no unsupported reasons) | `ml_core/explain.py` templates filled only with computed values | ✅ tests: no invented skills, largest contributor named |
| 6.8 | Feature importance for job-role model | `artifacts/figures/feature_importance_rf.png`, `permutation_importance_best.png`, `shap_summary.png` | ✅ impurity + permutation (test set) + SHAP |

### 7. Visualisation and model evaluation
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 7.1 | Dataset distribution charts | `artifacts/figures/dist_job_role_classes.png`, `dist_internships.png` | ✅ |
| 7.2 | Model accuracy and F1 comparison | `artifacts/figures/model_comparison.png` | ✅ |
| 7.3 | Confusion matrices | `artifacts/figures/confusion_matrix_dt.png`, `confusion_matrix_rf.png` | ✅ |
| 7.4 | Feature importance chart | `artifacts/figures/feature_importance_rf.png`, `permutation_importance_best.png` | ✅ |
| 7.5 | Internship similarity ranking chart | `artifacts/figures/similarity_ranking_demo.png` | ✅ (DEMO profile) |
| 7.6 | Skill matching visualisation | `artifacts/figures/skill_match_demo.png` | ✅ (DEMO profile) |

### 8. Save models and artifacts
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 8.1 | Decision Tree model | `artifacts/models/dt.joblib` | ✅ |
| 8.2 | Random Forest model | `artifacts/models/rf.joblib` | ✅ |
| 8.3 | Best job-role prediction model | `artifacts/models/best_model.joblib` | ✅ |
| 8.4 | Preprocessing pipeline and feature schema | `artifacts/models/preprocess.joblib`, `artifacts/config/feature_schema.json` | ✅ schema includes vocabulary, classes and scope thresholds |
| 8.5 | TF-IDF vectorizer | `artifacts/vectorizers/tfidf.joblib` | ✅ |
| 8.6 | Sentence Transformer model or local reference | `artifacts/models/sentence_model/` (git-ignored, D-020) + `scripts/setup_sentence_model.py` | ✅ setup script output verified byte-identical against manifest |
| 8.7 | Hybrid recommendation configuration | `artifacts/config/hybrid_config.json` | ✅ |
| 8.8 | Reusable recommendation functions | `ml_core/recommender.py` (+ eligibility, explain) | ✅ |
| 8.9 | LLM extraction configuration and fallback functions | `artifacts/config/llm_config.json`, `ml_core/llm_extract.py` | ✅ |
| 8.10 | Model evaluation metrics | `artifacts/metrics/` | ✅ |
| 8.11 | Visualisation images | `artifacts/figures/` (12 PNGs) | ✅ |
| 8.12 | Cleaned internship dataset | `artifacts/data/internships_clean.csv` | ✅ 8,207 rows |
| 8.13 | Required model metadata | `artifacts/manifest.json` | ✅ SHA-256 per file, versions, best model, pinned revision |
| 8.14 | Sample inference functions proving reload without retraining | `notebooks/eligo_engine.ipynb` §3.7 | ✅ restart-safe reload through `load_bundle()`; same top-5 ranking asserted |
| 8.15 | **Deliverable:** complete executable notebook with all of the above | `notebooks/eligo_engine.ipynb` | ✅ executes top to bottom with nbconvert (exit 0) |

---

## Part B — Django web application

### 9. Technology stack
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 9.1 | Frontend: HTML5, CSS3, JavaScript, Bootstrap 5 | `templates/`, `static/css/theme.css`, `static/js/`, vendored Bootstrap 5.3.9 | ✅ |
| 9.2 | Backend: Django 5.2 LTS | `config/`, six apps | ✅ Django 5.2.19 |
| 9.3 | Database: SQLite | `config/settings.py` (SQLite) | ✅ |
| 9.4 | ML: scikit-learn, Joblib | `ml_core/`, joblib loads in `ml_core.artifacts` | ✅ |
| 9.5 | AI recommendation: TF-IDF, Sentence Transformers, cosine similarity | `recommendations/services.py` → `ml_core.recommender` | ✅ |
| 9.6 | LLM: optional Ollama | `ml_core/llm_extract.py`, `recommendations/services.py` (D-024) | ✅ live in the web app (top 3 per run; method shown) |
| 9.7 | XAI: feature-based recommendation explanations | `ml_core/explain.py`, recommendation detail pages | ✅ |
| 9.8 | Visualisation: Chart.js | `static/vendor/chartjs/`, `static/js/charts.js` (job-role probabilities + feature importance, admin recommendations per internship, model comparison) | ✅ |

### 10. Database tables
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 10.1 | Users (name, email, mobile, password hash, user_type, registered_date, status) | `accounts/models.py` `User` | ✅ email login, Admin/Student, Active/Inactive synced to is_active |
| 10.2 | Student_Profiles | `students/models.py` `StudentProfile` (+ `career_skills`, D-022) | ✅ |
| 10.3 | Internships | `internships/models.py` `Internship` | ✅ |
| 10.4 | Assessments | `assessments/models.py` `Assessment` | ✅ |
| 10.5 | Assessment_Questions | `assessments/models.py` `Question` (A–D validator, marks ≥ 0) | ✅ |
| 10.6 | Assessment_Attempts | `assessments/models.py` `Attempt` (one In_Progress constraint, deadline) | ✅ |
| 10.7 | Student_Answers | `assessments/models.py` `Answer` (unique per question) | ✅ |
| 10.8 | Internship_Recommendations | `recommendations/models.py` `InternshipRecommendation` (run_id, explanation, method) | ✅ |
| 10.9 | Job_Role_Predictions | `recommendations/models.py` `JobRolePrediction` (probability, scope, top features) | ✅ |
| 10.10 | Django authentication + secure password hashing | `accounts/`, Django PBKDF2 hashers | ✅ |
| 10.11 | Foreign keys, constraints, JSON fields, migrations | all apps' `models.py` + committed migrations | ✅ FKs (PROTECT for history), constraints, JSONFields |

### 11. Admin module
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 11.1.1 | Admin login | `accounts/views.py` (email login) | ✅ |
| 11.1.2 | Admin change password | `accounts:password_change` | ✅ |
| 11.1.3 | Admin logout | `accounts:logout` (POST) | ✅ |
| 11.2.1 | Dashboard: total students | `adminpanel/services.py` `dashboard_counts` | ✅ |
| 11.2.2 | Dashboard: total internships | `adminpanel/services.py` | ✅ |
| 11.2.3 | Dashboard: total assessments | `adminpanel/services.py` | ✅ |
| 11.2.4 | Dashboard: qualified / not-qualified students | `adminpanel/services.py` (qualified = any attempt > 60%, same rule as the gate) | ✅ |
| 11.2.5 | Dashboard: total recommendations | `adminpanel/services.py` | ✅ |
| 11.3.1 | View registered students | `adminpanel:students` | ✅ |
| 11.3.2 | View student academic profiles and skills | `adminpanel:student_detail` | ✅ incl. career skills |
| 11.3.3 | View student assessment results | `adminpanel:student_detail` | ✅ |
| 11.3.4 | View student internship recommendations | `adminpanel:student_detail` | ✅ |
| 11.3.5 | Activate / deactivate students | `adminpanel:student_toggle` (POST) | ✅ |
| 11.4.1 | Add internship | `internships:admin_add` | ✅ |
| 11.4.2 | View internships | `internships:admin_list` | ✅ |
| 11.4.3 | Update internship | `internships:admin_edit` | ✅ |
| 11.4.4 | Activate / deactivate internship | `internships:admin_toggle` (POST) | ✅ |
| 11.4.5 | Form fields: company, job role, qualification, skills, location, stipend, duration, eligibility criteria, deadline | `internships/forms.py` `InternshipForm` | ✅ all spec fields required; skills normalised with suggestions |
| 11.5.1 | Create qualification-based assessment | `assessments:admin_add` | ✅ |
| 11.5.2 | View / update / deactivate assessment | `assessments:admin_list/admin_edit/admin_toggle` | ✅ activation needs questions |
| 11.5.3 | Add MCQ with four options and correct answer | `assessments:question_add` `QuestionForm` | ✅ |
| 11.5.4 | View / update / delete questions | `assessments:questions/question_edit/question_delete` | ✅ answered questions protected |
| 11.6.1 | View student assessment results | `adminpanel:results` | ✅ |
| 11.6.2 | View obtained marks and percentage | `adminpanel:results` | ✅ |
| 11.6.3 | View qualified / not-qualified status | `adminpanel:results` (filter by result) | ✅ |
| 11.7.1 | View student-wise recommended internships | `adminpanel:recommendations`, `recommendation_run` | ✅ |
| 11.7.2 | View match scores and ranking | `adminpanel:recommendation_run` | ✅ |
| 11.7.3 | View recommendation explanations | `adminpanel:recommendation_detail` | ✅ |
| 11.7.4 | View matched and missing skills | `adminpanel:recommendation_run/detail` | ✅ |
| 11.8.1 | View student job-role predictions | `adminpanel:ml` predictions table | ✅ |
| 11.8.2 | View saved ML model evaluation results | `adminpanel:ml` metrics.json + manifest-listed figures | ✅ |

### 12. Student module
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 12.1.1 | Student registration | `accounts:register` | ✅ |
| 12.1.2 | Login | `accounts:login` | ✅ |
| 12.1.3 | Update profile | `students:profile_edit`, `students:account_edit` | ✅ |
| 12.1.4 | Change password | `accounts:password_change` | ✅ |
| 12.1.5 | Logout | `accounts:logout` | ✅ |
| 12.2.1 | Update qualification and specialisation | `students/forms.py` `StudentProfileForm` | ✅ |
| 12.2.2 | Update college and academic percentage | `students/forms.py` | ✅ |
| 12.2.3 | Add / update skills | `students/forms.py`, `static/js/profile.js` (tag input with suggestions, searchable career-skill picker; D-022, D-026) | ✅ |
| 12.2.4 | Select career interests | `students/forms.py` | ✅ |
| 12.2.5 | Select preferred job role and location | `students/forms.py` | ✅ |
| 12.3.1 | Dashboard: available internships | `students/services.py` `dashboard_context` | ✅ |
| 12.3.2 | Dashboard: available assessments | `dashboard_context` → `available_assessments` | ✅ |
| 12.3.3 | Dashboard: latest assessment result | `dashboard_context` | ✅ |
| 12.3.4 | Dashboard: recommended internships | `dashboard_context` | ✅ |
| 12.3.5 | Dashboard: predicted job role | `dashboard_context` | ✅ |
| 12.4.1 | View active internships | `internships:list` | ✅ |
| 12.4.2 | Search by qualification, job role, location | `internships:list` (keyword, qualification, job role, location) | ✅ |
| 12.4.3 | View internship details and eligibility criteria | `internships:detail` (every gate with its reason) | ✅ |
| 12.5.1 | View qualification-based assessments | `assessments:list` | ✅ |
| 12.5.2 | Select and start assessment | `assessments:start` (server deadline, resume) | ✅ |
| 12.5.3 | Attempt MCQ questions | `assessments:exam` + autosave | ✅ |
| 12.5.4 | View remaining time | `static/js/timer.js` (server remaining seconds; pill navy → amber ≤5 min → red ≤1 min, with text labels) | ✅ |
| 12.5.5 | Submit assessment | `assessments:submit` | ✅ |
| 12.5.6 | Auto-submit when time expires | `timer.js` auto-submit + server lazy finalise | ✅ |
| 12.6.1 | Result: total questions | `assessments:result` | ✅ |
| 12.6.2 | Result: correct answers | `assessments:result` | ✅ |
| 12.6.3 | Result: obtained marks | `assessments:result` | ✅ |
| 12.6.4 | Result: assessment percentage, `(obtained / total) × 100` | `assessments/services.py` (Decimal, unrounded) | ✅ |
| 12.6.5 | Result: qualified / not-qualified status | `assessments/services.py` (strictly > 60) | ✅ |
| 12.7.1 | Check assessment and qualification eligibility | `recommendations/services.py` `generate_recommendations` | ✅ |
| 12.7.2 | Analyse student skills and academic profile | `recommendations/services.py` | ✅ |
| 12.7.3 | Match student profile with internship requirements | `recommendations/services.py` → `ml_core.recommender.recommend` | ✅ |
| 12.7.4 | Generate hybrid AI-based recommendations | `recommendations:list` (POST generate) | ✅ |
| 12.7.5 | View ranked internships with match scores | `recommendations:list` (recommendation cards) | ✅ |
| 12.7.6 | View matched and missing skills | `recommendations:list/detail` | ✅ |
| 12.7.7 | View XAI recommendation reasons | `recommendations:detail` (gates, components, contributions) | ✅ |
| 12.8.1 | Predict job role from academic profile + available assessment features | `recommendations/services.py` `predict_job_role` (career skills only, D-022) | ✅ |
| 12.8.2 | View predicted job role | `recommendations:job_role` (confidence + scope states, D-021) | ✅ |
| 12.8.3 | View related internship opportunities | `recommendations/services.py` `related_internships` (D-016) | ✅ |

### 13. Django AI model integration
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 13.1 | Load trained job-role model with Joblib | `ml_core/artifacts.py` via `recommendations.services.get_bundle` | ✅ |
| 13.2 | Load fitted preprocessing pipeline and feature schema | `ml_core/artifacts.py` | ✅ |
| 13.3 | Load saved TF-IDF vectorizer | `ml_core/artifacts.py` | ✅ |
| 13.4 | Load Sentence Transformer model | `ml_core/artifacts.py` (local folder only, manifest-verified) | ✅ |
| 13.5 | Import reusable hybrid recommendation functions | `recommendations/services.py` imports `ml_core` | ✅ |
| 13.6 | Mandatory eligibility checks | `ml_core/eligibility.py` (incl. per-internship gate date) | ✅ |
| 13.7 | Similarity scores and ranked results | `ml_core/recommender.py` | ✅ |
| 13.8 | Optional LLM skill extraction integrated | `recommendations/services.py` (D-024) | ✅ live: top 3 results marked 'LLM (local Ollama)', rest rule-based |
| 13.9 | Explainable recommendations | `ml_core/explain.py` → stored `explanation` | ✅ |
| 13.10 | Save predictions and recommendations to SQLite | `recommendations/services.py` (append-only runs) | ✅ |
| 13.11 | Do not retrain models inside Django | load-only artifacts; `test_new_internship_scored_without_refit` | ✅ |
| 13.12 | Use same preprocessing and recommendation configs as notebook | shared `ml_core/` + `artifacts/config/` | ✅ |

### 14. End-to-end processing rules
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 14.1 | Student registers and completes academic profile | `accounts:register` → `students:profile_edit` | ✅ |
| 14.2 | Student searches available internships | `internships:list` | ✅ |
| 14.3 | Student attempts qualification-based assessment | `assessments:*` | ✅ |
| 14.4 | System automatically evaluates assessment | `assessments/services.py` | ✅ |
| 14.5 | Score strictly above 60% satisfies assessment eligibility | `assessments/services.py`, `ml_core/eligibility.py` | ✅ |
| 14.6 | Check mandatory qualifications and other explicit eligibility rules | `ml_core/eligibility.py` | ✅ |
| 14.7 | Hybrid engine ranks only eligible internships | `ml_core/recommender.py` (gates first) | ✅ |
| 14.8 | Display scores, matched skills, missing skills, explanations | recommendation cards, detail page, XAI table | ✅ |
| 14.9 | ML model predicts job-role category separately | `recommendations:job_role` | ✅ |
| 14.10 | All important results stored in the database | attempts, answers, recommendation runs, predictions in SQLite | ✅ |
| 14.11 | Mandatory qualifications/thresholds never overridden by similarity scores | gates before scoring; tested + mutation-checked | ✅ |

### 15. User interface requirements
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 15.1 | Attractive academic and career-themed design | `static/css/theme.css` (CLAUDE.md tokens, D-023), `docs/screenshots/` | ✅ |
| 15.2 | Responsive Bootstrap layouts | templates; every page shot at 1440 and 390 px in `docs/screenshots/` | ✅ |
| 15.3 | Separate admin and student dashboards | student top bar + journey + stat band; admin navy sidebar + stat band + charts | ✅ |
| 15.4 | Simple forms and navigation | `partials/form.html`, active-tab navigation, admin breadcrumbs | ✅ |
| 15.5 | Searchable internship listings | `internships:list` (filters, empty state, pagination) | ✅ |
| 15.6 | Online MCQ interface with timer | `assessments:exam`, `timer.js`, `exam.js` (timer pill, palette, one question per view, confirm modal; D-026) | ✅ |
| 15.7 | Recommendation cards with match scores | `templates/recommendations/list.html` (score ring, breakdown bar, chips, explain section, async AI second opinion) | ✅ |
| 15.8 | Matched and missing skills visualisation | matched (solid green) and missing (dashed orange) chips, breakdown bar | ✅ |
| 15.9 | Job-role prediction result page | `recommendations:job_role` (hero or scope state, probability + feature charts, related internships) | ✅ |
| 15.10 | User-friendly validation and error messages | forms + messages, empty states | 🟨 specific messages in place; final copy pass in Phase 7 |
| 15.11 | Avoid unnecessary animations, complex dashboards, decorative elements | `theme.css` (150 ms colour/shadow + 2 px lift only, off under reduced motion), Chart.js animation off | ✅ |

### 16. Security and validation
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 16.1 | Django built-in authentication | `accounts/` | ✅ |
| 16.2 | Store passwords securely | Django PBKDF2 (tests use a fast hasher only) | ✅ |
| 16.3 | Protect admin and student routes | `accounts/decorators.py` `student_required`/`admin_required` | ✅ |
| 16.4 | Validate student profiles and assessment inputs | forms + `assessments.services._validate` | ✅ |
| 16.5 | Prevent duplicate assessment submissions | `assessments/services.py` `submit` (D-011) | ✅ sequential duplicates tested; parallel test in Phase 6 |
| 16.6 | Enforce assessment timing on the server | `assessments/services.py` (deadline + 10 s grace, lazy finalise) | ✅ |
| 16.7 | Don't expose correct answers during exams | `assessments/services.py` `exam_questions` (.values() without correct_option) | ✅ |
| 16.8 | Restrict students to their own results | `get_object_or_404(..., student=request.user)` everywhere | ✅ 404 for others' objects |
| 16.9 | Load ML models only from trusted local files | `ml_core/artifacts.py` SHA-256 manifest; figure view serves manifest-listed files only | ✅ |
| 16.10 | Handle missing model artifacts gracefully | `load_bundle` never raises; banner via context processor | ✅ |
| 16.11 | Preserve historical assessment scores | PROTECT FKs, append-only runs, retakes create new attempts | ✅ |

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
| 17.8 | Optional: Ollama + small local LLM | Ollama 0.40.18 + `qwen3:4b` (2.5 GB) | ✅ installed and verified (`ollama list`, live test) |
| 17.9 | Optional: pydantic | `requirements.txt` | ✅ 2.14.4 |
| 17.10 | Optional: shap | `requirements.txt` | ✅ 0.54.1 |
| 17.11 | No RAG, LangChain, ChromaDB, FAISS, cloud deploy, paid APIs | `requirements.txt` has none | ✅ (re-checked each phase) |

### 18. Testing requirements
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 18.1 | Student registration and login | `tests/django/test_accounts.py` (`test_register_*`, `test_login_by_email`, `test_inactive_*`, admin pages forbidden to students) + E2E register/login (`docs/E2E.md`) | ✅ |
| 18.2 | Admin internship management | `tests/django/test_internships.py` (`test_admin_add_*`, `test_admin_update_internship`, `test_toggle_is_post_only`, inactive hidden from students) | ✅ |
| 18.3 | Qualification-based assessment | `tests/django/test_assessments.py` (`test_students_only_see_matching_qualification_assessments`, `test_cannot_start_assessment_for_other_qualification`) | ✅ |
| 18.4 | Automatic assessment evaluation | `test_grading_decimal_and_threshold`, `test_unanswered_count_as_zero`, `test_duplicate_submission_rejected`, `test_late_submission_auto_submitted_uses_saved_answers_only`, `test_expired_attempt_finalised_on_page_load`, `tests/django/test_concurrency.py` (D-027) + E2E timer auto-submit | ✅ |
| 18.5 | Score above 60% eligibility (boundary: 60.00 → Not_Qualified) | `test_is_qualified_boundary` (60.00 → NQ, 60.01 → Q, 100, 0), `test_tiny_margin_above_sixty_qualifies_even_if_display_rounds_to_60`, `test_result_ring_marks_the_60_percent_threshold` + E2E DEMO B.Sc at exactly 60.00% → Not qualified | ✅ |
| 18.6 | Qualification eligibility checking | `tests/test_ml_core_eligibility.py` (`test_qualification_hierarchy`, gate tests), `test_detail_shows_failed_gate_reason` | ✅ |
| 18.7 | Content-based internship matching | `test_content_similarity_prefers_relevant`, `test_content_similarity_does_not_refit` | ✅ |
| 18.8 | Semantic similarity matching | `test_semantic_in_range`, `test_semantic_normalises_unnormalised_vectors`, `tests/test_integration_artifacts.py::test_semantic_ordering_real_model` (real all-MiniLM-L6-v2) | ✅ |
| 18.9 | Hybrid recommendation ranking | `test_hybrid_weights_applied`, `test_recommend_excludes_ineligible_even_if_most_similar`, `test_rank_tie_break_by_skill`, `test_load_hybrid_config_*` | ✅ |
| 18.10 | Matched skills and skill-gap explanation | `tests/test_ml_core_explain.py`, `tests/test_ml_core_skills.py`, `test_detail_shows_explanation_from_stored_values`, `test_recommendation_card_parts` | ✅ |
| 18.11 | Job-role prediction | `tests/test_ml_core_job_role.py`, `test_prediction_uses_only_career_skills`, `test_prediction_without_career_skills_asks_for_them`, `test_demo_cs_profile_confident_and_correct` (real model) | ✅ |
| 18.12 | Saved model integration | `tests/test_ml_core_artifacts.py` (manifest, tamper detection), `tests/test_integration_artifacts.py` (`test_real_bundle_loads_and_predicts`, `test_saved_embeddings_match_saved_model_and_data`) | ✅ |
| 18.13 | Missing model and invalid input handling | `test_load_bundle_tampered_returns_none`, `test_recommendations_page_without_artifacts_shows_banner`, `test_ml_page_without_artifacts_shows_message`, `test_invalid_option_or_foreign_question_rejected`, `test_career_skills_reject_value_not_in_model_vocab`, form validation tests | ✅ |
| 18.14 | Actual data for evaluation; illustrative test profiles clearly labelled, never presented as training data | `tests/django/test_seed_demo.py::test_all_demo_objects_labelled`, `tests/test_ml_core_demo.py`, `test_reset_demo_*`; metrics from the real Kaggle/Mendeley data (notebook) | ✅ |

### 19. Final development instructions
| ID | Requirement | Where implemented | Status |
|---|---|---|---|
| 19.1 | Complete executable notebook and Django source code | `notebooks/`, Django apps | ⬜ |
| 19.2 | Complete notebook before Django integration | phase order (3 before 4) | ⬜ |
| 19.3 | Only freely available datasets and pretrained models | `docs/DATASETS.md` | ⬜ |
| 19.4 | Two user roles: Admin and Student | `accounts/models.py` | ✅ |
| 19.5 | Every essential functional requirement implemented | this checklist | ⬜ |
| 19.6 | Reusable Python functions for recommendations and inference | `ml_core/` | ✅ |
| 19.7 | No retraining in Django | `ml_core/artifacts.py` (load only) | ✅ |
| 19.8 | No fabricated datasets, performance or predictions | whole project | ⬜ |
| 19.9 | Consistent model input features between training and inference | `artifacts/config/feature_schema.json` + Pipeline | ✅ |
| 19.10 | Deterministic fallback when LLM unavailable | `ml_core/llm_extract.py` | ✅ |
| 19.11 | Django migrations, requirements.txt, README | repo root | 🟨 requirements.txt done |
| 19.12 | Windows-compatible local demonstration | README, offline vendored assets | 🟨 assets vendored, no CDN |
| 19.13 | No integration with official government portal | scope | ✅ no portal integration |
| 19.14 | No internship allocation, payments, or employer recruitment modules | scope | ✅ none implemented |
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
- [x] **Step 8 (Ollama install): done 2026-11-24, Ollama 0.40.18.** History: The winget install was stopped on 2026-11-22. On 2026-11-24 a resumable `curl.exe -L -C -` download of `OllamaSetup.exe` to `%USERPROFILE%\Downloads\` was started in the background. When it finishes: run the installer (Krishna clicks Yes), then verify with `ollama --version`.
- [x] Step 11: session restarted, new skills loaded (2026-11-24)

### Phase 1 — Research and decisions
- [x] Last30days on all 4 topics + web supplements → `docs/RESEARCH.md` (2026-11-24; thin 30-day signal stated honestly)
- [x] Context7 docs: Django 5.2, sentence-transformers, scikit-learn 1.9, Chart.js 4, Bootstrap 5.3, Ollama `/api/chat` → `docs/RESEARCH.md` §5
- [x] DATASETS.md complete: name, URL, licence, rows/cols, column descriptions, synthetic yes/no, why chosen, rejected candidates
- [x] Raw data present in `data/raw/`: Student Career (SHA-256 verified against Mendeley) + Kaggle `merged_internships_dataset.csv` (8,483 × 13, size matches Kaggle, profiled 2026-11-24)
- [x] All decisions logged: D-005 datasets A, D-006 dataset B, D-007 qualification fields, D-008 assessment feature, D-009 Ollama model, D-010 UI kit, D-011 SQLite locking
- [x] Step 6 `ollama pull qwen3:4b`: done 2026-11-25 (Krishna approved)

### Phase 2 — Plan
- [x] Brainstorming → design `docs/superpowers/specs/2026-11-24-eligo-design.md` (approaches + decisions D-012…D-019)
- [x] writing-plans → `docs/PLAN.md`: 23 tasks for Phases 3–7, file list, data flow (notebook → artifacts → `ml_core.artifacts` → Django services → SQLite; `load_internships`; saved TF-IDF + sentence model for admin-added internships with the D-014 cache), typed `ml_core` public API, test plan mapped to every spec §18 scenario
- [x] Self-review: spec coverage, type consistency, Review Focus tests placed in their owning tasks

### Phase 3 — Notebook + ml_core
- [x] `ml_core/` built test-first (9 modules): `pytest tests` → 172 passed, 1 skipped (the live-Ollama test, which skips until the model is installed)
- [x] `jupyter nbconvert --to notebook --execute notebooks/eligo_engine.ipynb` → exit 0 (final run 2026-11-24)
- [x] Every spec §8 artifact saved + `manifest.json` (SHA-256); restart-safe reload test passes (same ranking, nothing retrained)
- [x] Real metrics at Phase 3 (test n=374): DT 0.8396 / 0.8604; RF 0.8904 / 0.9107. **Current, after the D-022 retrain (test n=330): Decision Tree acc 0.8030 / macro-F1 0.8048; Random Forest acc 0.8485 / macro-F1 0.8787 (best)**
- [x] `scripts/setup_sentence_model.py` re-creates the git-ignored sentence model and verifies it byte-for-byte against the manifest (D-020)
- [x] Live LLM output in notebook §3.5 (re-run 2026-11-25 with `qwen3:4b`)

### Phase 4 — Django backend
- [x] `python manage.py check` → 0 issues; `makemigrations --check` → no changes; `migrate` applied
- [x] `load_internships` → 8,207 real postings (0 text-hash mismatches); `seed_demo` → 3 DEMO students + 3 DEMO assessments
- [x] `pytest tests` → 311 passed, 1 skipped at the phase commit; after the model finished: 313 passed, 0 skipped
- [x] End-to-end smoke through the real views + real artifacts (rolled back): DEMO CS exam 80% Qualified, duplicate submit rejected, 10 recommendations in ~3.7 s, job role Artificial Intelligence 95% confident, all admin pages 200
- [x] D-022 career-skills fix applied end to end (multi-select from feature_schema.json, prediction uses only career skills, DEMO CS confident + test)

### Phase 5 — UI and design
- [x] Hallmark study → D-023; tokens + layouts in `static/css/theme.css`; signature components on every student and admin page (D-026)
- [x] `warm_llm` command + non-blocking warm-up on `runserver` (D-025); documented in the README demo checklist
- [x] Recommendations render in 3.26 s (measured in the browser, 8,207 internships); the top 3 cards show "AI second opinion: checking…" and the three LLM checks finished 6.8 s later without blocking the page
- [x] Playwright screenshots of every page at 1440 and 390 px → `docs/screenshots/` (real flows: DEMO CS 80.00% Qualified, DEMO B.Sc exactly 60.00% Not qualified)
- [x] Audit loop: sloplint static tier clean apart from recorded waivers (render tier needs puppeteer-core, not installed); screenshot-review fixes applied and re-shot
- [x] `pytest tests` → all pass; the strict xfail on middle-dot meta strings is removed and the test passes

### Phase 6 — Testing
- [x] Every spec §18 scenario mapped to real tests (rows 18.1–18.14)
- [x] New: `tests/django/test_concurrency.py` (two threads, real SQLite file). It found a real bug, fixed by SQLite IMMEDIATE transactions (D-027); passes 10/10, fails 3/3 without the fix
- [x] New: `tests/test_integration_artifacts.py` checks the real bundle, embeddings vs model and data, and real semantic ordering
- [x] New: `python manage.py reset_demo` (D-028) with `test_reset_demo_never_touches_non_demo_data` (field-by-field snapshot; mutation-checked)
- [x] `puppeteer-core` 25.17.0 dev dependency (D-029); sloplint render tier now runs and found a field-contrast issue (fixed)
- [x] Playwright E2E per BUILD_PROMPT Phase 6.2 and the README viva script, recorded in `docs/E2E.md` (all steps PASS; found a stale-exam-after-Back bug, fixed with `@never_cache` + `test_exam_page_is_never_cached`)
- [x] Notebook re-executed with `nbconvert` (exit 0)

## PENDING – Ollama (tracker)
Items that need a live Ollama. Everything else goes ahead without it, because the project never depends on Ollama and the rule-based fallback always works.

| Item | What waits | Status |
|---|---|---|
| Phase 0 step 8 | Install Ollama + `ollama --version` | ✅ 2026-11-24: Ollama 0.40.18 installed (signed installer, Krishna clicked Yes), server answers on :11434 |
| Phase 1 step 6 | `ollama pull qwen3:4b` (~2.5 GB; DECIDED in D-009) | ✅ 2026-11-25: pulled, SHA-256 digest verified by Ollama |
| Phase 3.5 | Live LLM test + live output in notebook §3.5 | ✅ 2026-11-25: live test passes; notebook re-run; web app uses the LLM for the top 3 (two bugs found and fixed on the way, see DECISIONS D-009) |
