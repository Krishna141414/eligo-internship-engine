# PROJECT SPEC — Eligo (AI-Based Internship Recommendation Engine for PM Internship Scheme)

> Original requirement document, the source of truth for this project. Only the formatting was cleaned up; the content is unchanged.

## Complete academic project development prompt

Project Title: AI-Based Internship Recommendation Engine for PM Internship Scheme

Develop a complete, functional academic project using Python, Jupyter Notebook, Django, SQLite, Machine Learning, Hybrid Recommendation Systems, LLM-Based Skill Analysis, and Explainable AI.

The project must demonstrate how student qualifications, academic profiles, skills, career interests, and assessment performance can be used to recommend suitable internships and predict job roles.

The project will have two development stages:

- Jupyter Notebook: Dataset preprocessing, AI/ML development, evaluation, and saving models.
- Django Web Application: Complete Admin and Student modules, online assessments, model integration, internship recommendations, and explanations.

The application must be suitable for demonstration on a standard Windows laptop without paid services or cloud deployment.

# PART A: JUPYTER NOTEBOOK DEVELOPMENT

## 1. Dataset Requirements

Use freely available public datasets containing relevant information such as:

- Student qualifications, academic details, and skills.
- Job roles and career-related attributes.
- Internship opportunities, descriptions, qualifications, and required skills.
- Assessment-related features where supported by the dataset.

Provide dataset download URLs and column descriptions. Do not fabricate training data, labels, or evaluation results.

## 2. Data Preprocessing

- Load and analyze datasets.
- Handle missing values and duplicates.
- Encode categorical variables.
- Process academic and skill-related features.
- Clean internship descriptions.
- Prepare training and testing datasets.
- Prevent data leakage.

## 3. ML-Based Job Role Prediction

Train and compare:

- Decision Tree Classifier.
- Random Forest Classifier.

Predict suitable job-role categories using student academic information, skills, and assessment features where supported by the training dataset.

Evaluate using:

- Accuracy.
- Precision.
- Recall.
- F1-Score.
- Confusion Matrix.
- Classification Report.

Select and save the best-performing model.

## 4. Hybrid AI Internship Recommendation Engine

Implement:

- Student profile and skill analysis.
- Assessment eligibility checking (score strictly above 60%).
- Mandatory internship qualification checking.
- Content-based filtering using TF-IDF and cosine similarity.
- Semantic matching using Sentence Transformers.
- Hybrid recommendation score calculation.
- Ranking of eligible internships.
- Matched skill and missing skill identification.

Use a lightweight Sentence Transformer such as all-MiniLM-L6-v2.

The recommendation engine must use actual internship records and reusable Python functions.

## 5. LLM-Based Skill Analysis

Implement optional local LLM-based analysis using a small instruct model through Ollama, where feasible.

- Extract student skills.
- Extract internship-required skills.
- Normalize skill names.
- Compare student and internship requirements.
- Identify skill gaps.
- Validate structured outputs.

Provide rule-based fallback when the LLM is unavailable.

Do not implement RAG or a vector database.

## 6. Explainable AI

Generate explanations showing:

- Qualification eligibility.
- Assessment eligibility.
- Matched skills.
- Missing skills.
- Content and semantic similarity contributions.
- Final internship match score.

Explain actual recommendation factors rather than generating unsupported reasons.

Include feature importance for the job-role prediction model.

## 7. Visualization and Model Evaluation

Generate and save:

- Dataset distribution charts.
- Model accuracy and F1-score comparison.
- Confusion matrices.
- Feature importance chart.
- Internship similarity ranking chart.
- Skill matching visualization.

## 8. Save Models and Artifacts

Save:

- Decision Tree model.
- Random Forest model.
- Best job-role prediction model.
- Preprocessing pipeline and feature schema.
- TF-IDF vectorizer.
- Sentence Transformer model or local reference.
- Hybrid recommendation configuration.
- Reusable recommendation functions.
- LLM extraction configuration and fallback functions.
- Model evaluation metrics.
- Visualization images.
- Cleaned internship dataset.
- Required model metadata.

Provide sample inference functions to verify that saved models can be reloaded without retraining.

Notebook Deliverable: A complete executable Jupyter Notebook with trained job-role prediction models, a reusable hybrid recommendation engine, optional LLM analysis, explainable matching results, and saved artifacts ready for Django integration.

# PART B: DJANGO WEB APPLICATION DEVELOPMENT

## 9. Technology Stack

- Frontend: HTML5, CSS3, JavaScript, Bootstrap 5
- Backend: Python Django 5.2 LTS
- Database: SQLite
- Machine Learning: Scikit-learn, Joblib
- AI Recommendation: TF-IDF, Sentence Transformers, Cosine Similarity
- LLM: Optional Ollama
- Explainable AI: Feature-Based Recommendation Explanations
- Visualization: Chart.js

## 10. Database Tables

Create the following essential Django ORM models.

### Users

id, name, email, mobile_number,

password_hash, user_type (Admin / Student),

registered_date, status (Active / Inactive)

Use Django authentication and secure password hashing.

### Student_Profiles

id, student_id (FK Users),

qualification, specialization,

college_name, academic_percentage,

skills, career_interests,

preferred_job_role, preferred_location,

updated_date

### Internships

id, company_name, internship_title,

job_role, description,

required_qualification, specialization,

minimum_academic_percentage,

required_skills, location, stipend,

duration, work_mode,

eligibility_criteria, application_deadline,

status (Active / Inactive)

### Assessments

id, assessment_name, qualification,

specialization, duration_minutes,

status (Active / Inactive)

### Assessment_Questions

id, assessment_id (FK),

question_text, option_a, option_b,

option_c, option_d, correct_option, marks

### Assessment_Attempts

id, student_id (FK),

assessment_id (FK), start_time,

submission_time, total_marks,

obtained_marks, score_percentage,

result (Qualified / Not_Qualified),

status (In_Progress / Submitted / Auto_Submitted)

### Student_Answers

id, attempt_id (FK),

question_id (FK), selected_option,

correct_option, is_correct, marks_obtained

### Internship_Recommendations

id, student_id (FK),

internship_id (FK),

assessment_attempt_id (FK),

qualification_match, skill_match_score,

semantic_similarity_score,

final_match_score, recommendation_rank,

matched_skills, missing_skills,

recommendation_reason, generated_date

### Job_Role_Predictions

id, student_id (FK),

assessment_attempt_id (FK),

predicted_job_role, model_name,

model_version, predicted_date

Use appropriate foreign keys, constraints, JSON fields, and Django migrations.

## 11. ADMIN MODULE

### 11.1 Authentication

- Admin Login.
- Change Password.
- Logout.

### 11.2 Admin Dashboard

- View Total Students.
- View Total Internships.
- View Total Assessments.
- View Qualified / Not Qualified Students.
- View Total Recommendations.

### 11.3 Student Management

- View Registered Students.
- View Student Academic Profiles and Skills.
- View Assessment Results.
- View Internship Recommendations.
- Activate / Deactivate Students.

### 11.4 Internship Management

- Add Internship.
- View Internships.
- Update Internship.
- Activate / Deactivate Internship.

Internship forms must include company, job role, required qualification, skills, location, stipend, duration, eligibility criteria, and deadline.

### 11.5 Assessment and MCQ Management

- Create Qualification-Based Assessment.
- View / Update / Deactivate Assessment.
- Add MCQ Questions with Four Options and Correct Answer.
- View / Update / Delete Questions.

### 11.6 Assessment Result Monitoring

- View Student Assessment Results.
- View Obtained Marks and Percentage.
- View Qualified / Not Qualified Status.

### 11.7 Recommendation Monitoring

- View Student-Wise Recommended Internships.
- View Internship Match Scores and Ranking.
- View Recommendation Explanations.
- View Matched and Missing Skills.

### 11.8 ML Prediction Monitoring

- View Student Job Role Predictions.
- View Saved ML Model Evaluation Results.

## 12. STUDENT MODULE

### 12.1 Registration and Login

- Student Registration.
- Login.
- Update Profile.
- Change Password.
- Logout.

### 12.2 Academic Profile

- Update Qualification and Specialization.
- Update College and Academic Percentage.
- Add / Update Skills.
- Select Career Interests.
- Select Preferred Job Role and Location.

### 12.3 Dashboard

- View Available Internships.
- View Available Assessments.
- View Latest Assessment Result.
- View Recommended Internships.
- View Predicted Job Role.

### 12.4 Internship Search

- View Active Internships.
- Search by Qualification, Job Role, and Location.
- View Internship Details and Eligibility Criteria.

### 12.5 Online Assessment

- View Qualification-Based Assessments.
- Select and Start Assessment.
- Attempt MCQ Questions.
- View Remaining Time.
- Submit Assessment.
- Auto Submit When Time Expires.

### 12.6 Assessment Results

- View Total Questions.
- View Correct Answers.
- View Obtained Marks.
- View Assessment Percentage.
- View Qualified / Not Qualified Status.

Assessment Score (%) = (Obtained Marks / Total Possible Marks) × 100

### 12.7 AI-Based Internship Recommendations

- Check Assessment and Qualification Eligibility.
- Analyze Student Skills and Academic Profile.
- Match Student Profile with Internship Requirements.
- Generate Hybrid AI-Based Recommendations.
- View Ranked Internships with Match Scores.
- View Matched and Missing Skills.
- View Explainable AI Recommendation Reasons.

### 12.8 ML-Based Job Role Prediction

- Predict Suitable Job Role Using Academic Profile and Available Assessment Features.
- View Predicted Job Role.
- View Related Internship Opportunities.

## 13. DJANGO AI MODEL INTEGRATION

Integrate saved Jupyter Notebook artifacts.

- Load the trained job-role prediction model using Joblib.
- Load the fitted preprocessing pipeline and feature schema.
- Load the saved TF-IDF vectorizer.
- Load the Sentence Transformer model.
- Import reusable hybrid recommendation functions.
- Implement mandatory eligibility checks.
- Generate internship similarity scores and ranked results.
- Integrate optional LLM skill extraction.
- Generate explainable recommendations.
- Save predictions and recommendations to SQLite.

Do not retrain models inside Django.

Use the same preprocessing and recommendation configurations developed in the notebook.

## 14. END-TO-END PROCESSING RULES

- Student registers and completes the academic profile.
- Student searches available internships.
- Student attempts a qualification-based assessment.
- The system automatically evaluates the assessment.
- Students scoring strictly above 60% satisfy the assessment eligibility condition.
- The system checks mandatory internship qualifications and other explicit eligibility rules.
- The hybrid AI engine ranks only eligible internships.
- The system displays recommendation scores, matched skills, missing skills, and explanations.
- The ML model predicts a suitable job-role category separately.
- All important results are stored in the database.

Mandatory qualifications and assessment thresholds must never be overridden by AI similarity scores.

## 15. USER INTERFACE REQUIREMENTS

- Attractive academic and career-themed design.
- Responsive Bootstrap layouts.
- Separate Admin and Student dashboards.
- Simple forms and navigation.
- Searchable internship listings.
- Online MCQ assessment interface with timer.
- Recommendation cards with match scores.
- Matched and missing skills visualization.
- Job-role prediction result page.
- User-friendly validation and error messages.

Avoid unnecessary animations, complex dashboards, and nonfunctional decorative elements.

## 16. SECURITY AND VALIDATION

- Use Django's built-in authentication.
- Store passwords securely.
- Protect Admin and Student routes.
- Validate student profiles and assessment inputs.
- Prevent duplicate assessment submissions.
- Enforce assessment timing on the server.
- Do not expose correct answers during examinations.
- Restrict student access to their own results.
- Load ML models only from trusted local files.
- Handle missing model artifacts gracefully.
- Preserve historical assessment scores.

## 17. SOFTWARE REQUIREMENTS

Development Tools

- Python 3.12
- JupyterLab
- Visual Studio Code
- Django 5.2 LTS
- SQLite
- Chrome / Edge

Python Libraries

- numpy
- pandas
- scikit-learn
- scipy
- joblib
- matplotlib
- seaborn
- sentence-transformers
- torch
- django
- openpyxl (if Excel datasets are used)

Optional

- Ollama and a small local LLM
- pydantic for structured LLM validation
- shap for advanced ML explainability

Do not introduce RAG, LangChain, ChromaDB, FAISS, cloud deployment, or paid APIs unless an additional documented requirement justifies them.

## 18. TESTING REQUIREMENTS

Test the following scenarios:

- Student Registration and Login.
- Admin Internship Management.
- Qualification-Based Assessment.
- Automatic Assessment Evaluation.
- Score Above 60% Eligibility.
- Qualification Eligibility Checking.
- Content-Based Internship Matching.
- Semantic Similarity Matching.
- Hybrid Recommendation Ranking.
- Matched Skills and Skill Gap Explanation.
- Job Role Prediction.
- Saved Model Integration.
- Missing Model and Invalid Input Handling.

Use actual data for model evaluation and clearly identified illustrative test profiles for functional demonstration. Do not present illustrative records as real training data.

## 19. FINAL DEVELOPMENT INSTRUCTIONS

- Generate complete executable Jupyter Notebook and Django application source code.
- Complete notebook development before Django integration.
- Use only freely available datasets and pretrained models.
- Implement the two user roles: Admin and Student.
- Implement every essential functional requirement specified above.
- Use reusable Python functions for AI recommendations and model inference.
- Do not retrain machine learning models in Django.
- Do not fabricate datasets, model performance, or prediction results.
- Maintain consistent model input features between training and inference.
- Handle optional LLM unavailability through deterministic fallback.
- Include Django migrations, requirements.txt, and README.
- Provide a Windows-compatible local demonstration.
- Do not integrate with the official government internship portal.
- Do not implement actual internship allocation, payments, or employer recruitment modules.
- Ensure all required buttons, pages, forms, and features are functional.

## FINAL PROJECT GOAL

Develop a complete academic prototype that demonstrates:

Student Academic Profile → Qualification-Based Assessment → Automatic Evaluation → Eligibility Verification → Hybrid AI Internship Recommendation → Explainable Matching Results → ML Job Role Prediction.

The completed system must clearly demonstrate the project's title through qualification-aware internship recommendations, content-based and semantic matching, optional LLM-based skill extraction, explainable AI, and supervised job-role prediction.

The project is an independent academic prototype developed in the context of the PM Internship Scheme and must not claim to provide official government internship allocation or integration.
