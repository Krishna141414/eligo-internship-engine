# Eligo — design (Phase 2)

Date: 2026-11-24 · Inputs: `docs/PROJECT_SPEC.md` (source of truth), `CLAUDE.md` (hard rules), `BUILD_PROMPT.md` (phases), `docs/DECISIONS.md` D-001…D-011, `docs/DATASETS.md`.
The plan built from this design is `docs/PLAN.md`.

## 1. Intent

An academic prototype for Krishna's B.Tech viva that shows, end to end and on one offline Windows laptop:
student profile → qualification-based MCQ assessment → automatic grading → **eligibility gates** → hybrid AI internship ranking (TF-IDF + Sentence-Transformer + skill overlap) → **explanations built only from computed values** → a separate ML job-role prediction (Decision Tree vs Random Forest).

The selling point is in the tagline: **eligibility-first, explainable**. Gates can't be overridden by similarity scores, and every number on screen can be traced to a real computation.

## 2. Goals, non-goals, anti-goals

**Goals**
- Every bullet in spec §§1–19 implemented, tested and mapped in `REQUIREMENTS_CHECKLIST.md`.
- The notebook and Django share one `ml_core/` package. Django only loads artifacts and runs inference.
- A demo that works with Wi-Fi off, with or without Ollama.
- Looks like a calm, professional govt-tech portal (CLAUDE.md design system).

**Non-goals (spec §19 / rule 17):** government portal integration, real allocation, payments, employer recruitment, cloud deploy, recommendation-accuracy claims (no relevance labels exist).

**Anti-goals (would be failures even if everything "works")**
- Any metric, label, prediction or explanation that wasn't actually computed (rule 6).
- An ineligible internship appearing in the ranked list.
- Correct answers reachable from the browser during an exam.
- A 500 page when artifacts are missing or Ollama is off.
- Training on synthetic data that looks rich but means nothing (why D-005 rejected three datasets).

## 3. Constraints

All 19 hard rules in `CLAUDE.md`, plus these from the Phase 1 findings:
- Job-role model input = **skills only** (D-005, D-008). Academic fields feed the gates, not the model.
- Internship text is composed from the posting's own fields (no description column) and flagged (D-007).
- The deadline gate uses `REFERENCE_DATE` = 2025-09-28 for imported postings (D-007).
- SQLite: `select_for_update` is a no-op, so the duplicate guard is a conditional UPDATE (D-011).
- No new runtime dependencies beyond `requirements.txt` (decided below, D-018).

## 4. Approaches considered (the how-choices the spec leaves open)

Each one is logged in `docs/DECISIONS.md` (D-012 … D-019) with the same reasoning.

### 4.1 Job-role feature representation (D-012)
- **A. Multi-hot skill vector over a canonical vocabulary**, learned inside the sklearn Pipeline from the training split only, through a small sklearn-compatible transformer `SkillBinarizer` in `ml_core`. Feature = one canonical skill, so feature importance reads as skills ("python", "web development"). Profile input uses the same vocabulary (tag input suggestions from `feature_schema.json`). **← chosen**
- B. TF-IDF over the raw skill string: works, but features become word fragments ("development", "app"), which is worse for explanations, and raw typos leak into features.
- C. Sentence embeddings as features: opaque to Decision Tree / RF importance, and heavier.

Why A: the most explainable option, leakage-safe (vocabulary fitted on train only), and it guarantees the same features at training and inference (spec §19 "consistent model input features").

### 4.2 Skill normalisation, one canonical vocabulary for both datasets (D-013)
- **A. One canonical skill vocabulary + synonym map in `ml_core/skills.py`**, used for student skills (dataset A, profile form), internship `Skills`, and LLM output. Rule-based extraction = split on `, ; / |` + lower/strip + synonym map + longest-phrase match against the vocabulary for free text. **← chosen**
- B. Separate vocabularies per dataset: skill overlap between students and internships would silently fail on spelling differences ("ms-excel" vs "excel").

The vocabulary is built in the notebook from the real tokens of both datasets (1,597 + 793 raw tokens), merged through the synonym map, and saved in `feature_schema.json` (job-role model vocabulary) and `skills_vocab.json` (full matching vocabulary).

### 4.3 Where internship embeddings live, and how new internships get scored (D-014)
- **A. Hybrid cache**: imported internships use the precomputed `artifacts/embeddings/internships.npy` (row order in `internship_index.json`, keyed by `source_id` + `text_hash`). Admin-added or edited internships are embedded with the **saved** sentence model when saved (or lazily at recommendation time if missing), stored in `Internship.embedding` (JSONField, 384 floats) with `embedding_text_hash`. Lookup order: DB embedding with matching hash → npy row with matching hash → compute now. TF-IDF vectors are computed on the fly with the saved vectorizer (sparse, about 8k docs, fast). **← chosen**
- B. Everything in the DB: 8k × 384 floats as JSON ≈ 30 MB in SQLite, slow to load. No benefit.
- C. Re-encode everything at startup: slow startup (minutes on CPU), wasteful.

### 4.4 Recommendation persistence and history (D-015)
- **A. Each "Generate recommendations" click is a new run**: rows keep `generated_date` + `run_id` and link to the qualifying attempt. Pages show the latest run, and admins can see earlier runs. Nothing is overwritten. **← chosen** (matches rule 12's spirit and spec §14 "results stored").
- B. Overwrite per student: loses history, and the attempt link goes stale.

### 4.5 "Related internships" for a predicted job role (D-016)
The model predicts 6 CS career fields, while most postings are non-tech (DATASETS.md).
- **A. Documented career-field → title/skill keyword map** (e.g. "Data Science" → data science, data analyst, machine learning, python…), ranked by semantic similarity to the career-field name, filtered by the student's gates, showing the top 5 with "why related". **← chosen**
- B. Semantic similarity to the label text only: unstable for short labels like "Development" and "Security".

### 4.6 Qualification hierarchy (D-017)
A documented map in `ml_core/eligibility.py`:
- "Any Graduate" accepts B.Tech/B.E., B.Sc, BCA, B.Com, BA, BBA, B.Des, plus any PG.
- "Any Postgraduate" accepts M.Tech, M.Sc, MCA, MBA, M.Com, MA.
- A specific degree accepts that degree, and the PG form of it where it's the same field (B.Tech → also M.Tech).
- "Diploma" accepts Diploma plus any graduate.
- "Pursuing" vs "completed" is not modelled: the profile collects the qualification being pursued or held.

Profile qualification choices come from this map, so the inputs line up with the gate.

### 4.7 Tests without new dependencies (D-018)
- **A. pytest + pytest-django with plain fixture functions in `tests/conftest.py`** (factory helpers written by hand). `unittest.mock` stands in for Ollama and HTTP. **← chosen**
- B. Add factory-boy + pytest-mock: nicer syntax, but adds dependencies beyond the locked stack for little gain.

### 4.8 Exam layout (D-019, the BUILD_PROMPT 5.4 DECIDE, settled now because it shapes the views)
- **A. One question per view inside a single page** (all questions in the form, JS shows one at a time; palette grid jumps between them; without JS everything shows as a scrollable list). Autosave posts each answer. **← chosen**: matches the palette design, needs one server round-trip per answer save rather than per question view, and degrades gracefully.
- B. A server page per question: more requests, and back-button edge cases with the timer.
- C. Scroll-only list: the palette loses its meaning.

## 5. Architecture and data flow

```
data/raw/*  ──notebook (imports ml_core)──►  artifacts/  ──ml_core.artifacts.load_bundle()──►  recommendations/services.py  ──►  SQLite
   │                                           ├ models/{dt,rf,best_model}.joblib (Pipelines incl. preprocessing)
   │                                           ├ models/sentence_model/            (saved all-MiniLM-L6-v2)
   │                                           ├ vectorizers/tfidf.joblib
   │                                           ├ embeddings/internships.npy + internship_index.json
   │                                           ├ config/{hybrid_config,feature_schema,llm_config,skills_vocab}.json
   │                                           ├ metrics/metrics.json + classification reports
   │                                           ├ figures/*.png
   │                                           ├ data/internships_clean.csv
   │                                           └ manifest.json (SHA-256 of every file above + versions)
   └ management command load_internships ◄── artifacts/data/internships_clean.csv
```

- **Notebook**: EDA → clean (via `ml_core.preprocessing`) → train DT and RF (GridSearchCV on train) → evaluate → save → build TF-IDF + embeddings on the cleaned internships → hybrid demo on **DEMO-labelled** illustrative profiles + weight-sensitivity table → LLM vs fallback demo → manifest → restart-safe reload test.
- **Django**: `ml_core.artifacts.load_bundle()` runs once per process (module-level cache). It verifies `manifest.json` SHA-256 for each file before loading. On any failure it returns an `ArtifactStatus(ok=False, message=…)` and the site shows the banner. Assessments, profiles and search keep working.
- **Recommendation request**: latest qualifying attempt (score > 60, matching qualification) → gates on every active internship → hybrid scores **only for eligible** ones → rank → explanations → save the run → return eligible list + not-eligible list with reasons.

### 5.1 `ml_core` public API (signatures; docstrings and type hints get written first in Phase 3)

```python
# config.py
ARTIFACTS_DIR: Path; REFERENCE_DATE: date; PASS_THRESHOLD = Decimal("60")
@dataclass(frozen=True) class HybridWeights: content: float; semantic: float; skill: float   # sums to 1
def load_hybrid_config(path: Path | None = None) -> HybridConfig

# skills.py
def split_skills(text: str) -> list[str]
def normalise_skill(token: str, synonyms: Mapping[str, str]) -> str
def normalise_skills(text_or_list: str | Iterable[str], vocab: SkillVocab) -> list[str]   # sorted, unique, canonical
def extract_skills_rule_based(free_text: str, vocab: SkillVocab) -> list[str]
def compare_skills(student: Iterable[str], required: Iterable[str]) -> SkillComparison      # matched, missing, extra
class SkillBinarizer(BaseEstimator, TransformerMixin)                                       # multi-hot, vocab fit on train

# preprocessing.py
def clean_text(text: str) -> str                         # HTML, whitespace, boilerplate
def clean_internships(raw: pd.DataFrame) -> pd.DataFrame # D-007 rules + derived_fields + description_derived
def parse_stipend(text: str) -> StipendRange | None
def parse_deadline(text: str, year_hint: int) -> date | None
def parse_education(text: str) -> QualificationRule      # required_qualification, specialization, derived flag
def build_internship_text(row: Mapping) -> str
def build_student_text(profile: StudentProfileInput) -> str

# eligibility.py
GateResult = NamedTuple(passed: bool, reason: str, gate: str)
def check_status_and_deadline(internship, today: date) -> GateResult
def check_qualification(student_qual: str, required: str) -> GateResult
def check_specialization(student_spec: str, required: str | None) -> GateResult
def check_academic_percentage(student_pct: Decimal, minimum: Decimal) -> GateResult
def check_assessment(score: Decimal | None) -> GateResult                  # strictly > 60
def evaluate_gates(student, internship, assessment_score, today) -> EligibilityResult  # all gates, never short-circuits the reasons

# recommender.py
def content_similarity(student_text: str, internship_texts: Sequence[str], vectorizer) -> np.ndarray
def semantic_similarity(student_vec: np.ndarray, internship_vecs: np.ndarray) -> np.ndarray   # clipped [0, 1]
def skill_match_score(student_skills, required_skills) -> float                               # |matched| / |required|, 0 if none required
def hybrid_score(content, semantic, skill, weights: HybridWeights) -> ScoreBreakdown
def recommend(student, internships, assessment_score, bundle, *, today, top_n=10) -> RecommendationResult
#   -> eligible: list[RankedInternship] (rank, scores, contributions, matched, missing)
#   -> not_eligible: list[(internship_id, list[GateResult])]

# llm_extract.py
class SkillExtraction(BaseModel): skills: list[str]                       # pydantic
class SkillGapAnalysis(BaseModel): matched: list[str]; missing: list[str]; method: Literal["llm","rule_based"]
def ollama_available(base_url: str, timeout: float = 2.0) -> bool
def extract_skills(text: str, *, vocab, config: LLMConfig) -> ExtractionResult   # tries LLM, retries once, falls back
def analyse_gap(student_skills, internship_text, *, vocab, config) -> SkillGapAnalysis

# explain.py
def explain_recommendation(ranked: RankedInternship, gates: EligibilityResult, weights) -> Explanation  # dict + sentence
def explain_ineligible(gates: EligibilityResult) -> list[str]
def explain_job_role(prediction, top_features) -> JobRoleExplanation

# job_role.py
def build_input_frame(skills: Iterable[str], schema: FeatureSchema) -> pd.DataFrame   # validates against schema
def predict_job_role(skills, bundle) -> JobRolePrediction                              # label, proba, model name/version
def global_feature_importance(bundle, top_k=10) -> list[FeatureImportance]
def related_internship_keywords(career_field: str) -> list[str]                        # D-016 map

# artifacts.py
@dataclass class ArtifactBundle: ...; @dataclass class ArtifactStatus: ok: bool; message: str; missing: list[str]
def write_manifest(artifacts_dir: Path, extra: dict) -> Path
def verify_manifest(artifacts_dir: Path) -> ArtifactStatus
def load_bundle(artifacts_dir: Path | None = None) -> tuple[ArtifactBundle | None, ArtifactStatus]  # never raises
```

### 5.2 Django apps (BUILD_PROMPT folder structure, unchanged)
`accounts` (User, auth, role decorators, `create_admin`) · `students` (StudentProfile, dashboard, profile forms) · `internships` (Internship CRUD/search, `load_internships`) · `assessments` (Assessment, Question, Attempt, Answer, grading service, timer API) · `recommendations` (InternshipRecommendation, JobRolePrediction, services, `seed_demo`) · `adminpanel` (dashboard + monitoring views).

## 6. Decided by the spec / BUILD_PROMPT (not reopened)
Stack and versions; the 19 hard rules; folder structure; model list (DT + RF, best by macro-F1); evaluation metrics; artifact list; DB tables + BUILD_PROMPT additions; admin/student page lists; design tokens and signature components; test scenarios; phase order.

## 7. Left to the builder (settled during implementation, logged when made)
- Hybrid weights: default 0.35 / 0.40 / 0.25, final in Phase 3 with a sensitivity table on DEMO profiles.
- GridSearchCV grids (kept small for laptop speed).
- The exact Education keyword → qualification rule table (Phase 3, from the 1,139 real degree-mentioning values).
- Synonym map contents (built from real tokens, reviewed in the notebook).
- Copy text, empty-state wording, chart details (Phase 5 rules).

## 8. Self-run builder check
No subagent was dispatched (no request to spawn one), so I read the doc as a builder would. Questions that came up and where they're answered:
- "Which skill list feeds the model vs the matcher?" → §4.2: one canonical vocabulary; the model uses the train-fitted subset.
- "How does an admin-edited imported internship get a fresh embedding?" → §4.3 hash check.
- "Can a student without any qualifying attempt see anything?" → yes: the not-eligible list with the assessment gate reason, plus a CTA to take the assessment (spec §14).
- "Which attempt counts if there are several?" → the latest Submitted/Auto_Submitted attempt for an assessment matching the student's qualification with score > 60. Older attempts are kept and shown in history.
- "What about a student whose qualification has no matching assessment?" → the gate fails with the reason "No active assessment for your qualification yet"; the admin dashboard flags qualifications with no assessment.
Nothing left that only Krishna can answer.
