# EduPro Instructor Performance & Course Quality Evaluation

This project implements the Unified Mentor internship analysis requested for EduPro. It includes a Streamlit dashboard, a research paper, and an executive summary.

The dashboard is designed for restricted Windows environments: it avoids matplotlib and Streamlit's Arrow-backed chart/table rendering paths.

## Run the dashboard

1. Open a terminal in this folder.
2. Create a clean virtual environment: `python -m venv .venv_edupro`
3. Install the dependencies: `.\\.venv_edupro\\Scripts\\python.exe -m pip install -r requirements.txt`
4. Start the app: `.\\.venv_edupro\\Scripts\\python.exe -m streamlit run app.py`

If a previous Streamlit process is already running, stop it with `Ctrl+C` before restarting so the latest `app.py` is loaded. See `DEPLOYMENT.md` for GitHub and Streamlit Community Cloud instructions.
4. The bundled workbook is loaded automatically. The sidebar also supports uploading another workbook with the same four sheets: `Users`, `Teachers`, `Courses`, and `Transactions`.

## Analysis scope

The dashboard joins `Transactions` to `Teachers` by `TeacherID` and to `Courses` by `CourseID`. It uses transaction rows as observed enrollments/assignments and does not expose the Users sheet's email field.

## KPI definitions

- Average teacher rating: mean of `Teachers.TeacherRating`.
- Average course rating: mean of `Courses.CourseRating`.
- Consistency index: `100 * (1 - course-rating SD / 4)`, clipped at zero. A higher value indicates more stable course ratings among an instructor's observed assignments.
- Experience impact score: Pearson correlation between `YearsOfExperience` and `TeacherRating`, reported as a correlation in the dashboard and as a 0–100 score in the paper.
- Rating tiers: Low `< 3.0`, Mid `3.0–< 4.0`, High `>= 4.0`.
- Enrollment influence ratio: high-tier enrollment share divided by high-tier instructor share.

## Important data limitation

The workbook does not contain a single author/teacher field on each course. Instead, `TeacherID` appears in the transaction table, and the observed data contains 887 unique teacher-course pairs (about 14.8 teachers per course). Therefore, course ratings are used as assignment-level association measures; they should not be interpreted as causal instructor effects without confirming the data model.

## Deliverables

- `app.py`: interactive Streamlit dashboard.
- `research_paper.docx`: EDA, methodology, findings, limitations, and recommendations.
- `executive_summary.docx`: concise stakeholder briefing.
- `EduPro Online Platform.xlsx`: bundled input dataset used for the report.
