from pathlib import Path
from html import escape

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="EduPro | Instructor & Course Quality",
    page_icon="🎓",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_workbook(source):
    """Load the four workbook tabs and prepare the transaction-level join."""
    if isinstance(source, (str, Path)):
        sheets = pd.read_excel(source, sheet_name=None)
    else:
        sheets = pd.read_excel(source, sheet_name=None)

    required = {"Users", "Teachers", "Courses", "Transactions"}
    missing = required.difference(sheets)
    if missing:
        raise ValueError(f"Missing required sheet(s): {', '.join(sorted(missing))}")

    teachers = sheets["Teachers"].copy()
    courses = sheets["Courses"].copy()
    transactions = sheets["Transactions"].copy()
    users = sheets["Users"].copy()

    joined = (
        transactions.merge(teachers, on="TeacherID", how="left", validate="many_to_one")
        .merge(courses, on="CourseID", how="left", validate="many_to_one", suffixes=("_Teacher", "_Course"))
    )
    joined["RatingTier"] = pd.cut(
        joined["TeacherRating"],
        bins=[-np.inf, 3, 4, np.inf],
        labels=["Low (<3.0)", "Mid (3.0-<4.0)", "High (4.0+)"],
        right=False,
    )
    return users, teachers, courses, transactions, joined


def correlation(x, y):
    valid = pd.concat([x, y], axis=1).dropna()
    if len(valid) < 2 or valid.iloc[:, 0].nunique() < 2 or valid.iloc[:, 1].nunique() < 2:
        return np.nan
    return float(valid.iloc[:, 0].corr(valid.iloc[:, 1]))


def make_teacher_summary(joined):
    summary = (
        joined.groupby(["TeacherID", "TeacherName", "Gender", "Expertise", "Age", "YearsOfExperience", "TeacherRating"], observed=True)
        .agg(
            Enrollments=("TransactionID", "count"),
            UniqueLearners=("UserID", "nunique"),
            UniqueCourses=("CourseID", "nunique"),
            AvgAssignedCourseRating=("CourseRating", "mean"),
            MedianAssignedCourseRating=("CourseRating", "median"),
            CourseRatingSD=("CourseRating", "std"),
            PaidEnrollments=("Amount", lambda s: int((s > 0).sum())),
            Revenue=("Amount", "sum"),
        )
        .reset_index()
    )
    summary["ConsistencyIndex"] = (100 * (1 - summary["CourseRatingSD"].fillna(0) / 4)).clip(lower=0)
    summary["RatingTier"] = pd.cut(
        summary["TeacherRating"],
        bins=[-np.inf, 3, 4, np.inf],
        labels=["Low (<3.0)", "Mid (3.0-<4.0)", "High (4.0+)"],
        right=False,
    )
    return summary


def fmt(value, digits=2):
    return "—" if pd.isna(value) else f"{value:,.{digits}f}"


def render_table(obj, index=False):
    """Render tables as HTML so the dashboard does not require pyarrow or Styler."""
    table_html = pd.DataFrame(obj).to_html(index=index, escape=True)
    st.markdown(table_html, unsafe_allow_html=True)


def render_bar_chart(series, title, value_format="number"):
    """Lightweight HTML bar chart; avoids Streamlit's Arrow-backed chart path."""
    values = series.dropna().astype(float)
    max_value = float(values.max()) if not values.empty else 0.0
    rows = []
    for label, value in values.items():
        width = 0 if max_value == 0 else max(2, int(value / max_value * 100))
        shown = f"{value:,.0f}" if value_format == "count" else f"{value:.2f}"
        rows.append(
            f'<div class="edupro-bar-row"><span class="edupro-bar-label">{escape(str(label))}</span>'
            f'<span class="edupro-bar-track"><span class="edupro-bar-fill" style="width:{width}%"></span></span>'
            f'<span class="edupro-bar-value">{shown}</span></div>'
        )
    st.markdown(f'<div class="edupro-chart"><div class="edupro-chart-title">{escape(title)}</div>{"".join(rows)}</div>', unsafe_allow_html=True)


def render_scatter(df, x_col, y_col, title, size_col=None):
    """Render a compact SVG scatter plot without Altair, Vega, or pyarrow."""
    points = df[[x_col, y_col] + ([size_col] if size_col else [])].dropna().copy()
    if points.empty:
        st.info("No points match the current filters.")
        return
    width, height = 720, 340
    left, right, top, bottom = 58, 18, 18, 48
    x_min, x_max = float(points[x_col].min()), float(points[x_col].max())
    y_min, y_max = float(points[y_col].min()), float(points[y_col].max())
    x_span = x_max - x_min or 1.0
    y_span = y_max - y_min or 1.0
    size_min = float(points[size_col].min()) if size_col else 1.0
    size_max = float(points[size_col].max()) if size_col else 1.0
    size_span = size_max - size_min or 1.0
    marks = []
    for _, row in points.iterrows():
        cx = left + (float(row[x_col]) - x_min) / x_span * (width - left - right)
        cy = top + (1 - (float(row[y_col]) - y_min) / y_span) * (height - top - bottom)
        radius = 5 if not size_col else 5 + 9 * (float(row[size_col]) - size_min) / size_span
        tip = f"{x_col}: {float(row[x_col]):.2f} | {y_col}: {float(row[y_col]):.2f}"
        marks.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="#2E74B5" fill-opacity="0.70"><title>{escape(tip)}</title></circle>')
    svg = (
        f'<div class="edupro-chart"><div class="edupro-chart-title">{escape(title)}</div>'
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}" class="edupro-svg">'
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#98A2B3"/>'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#98A2B3"/>'
        f'{"".join(marks)}'
        f'<text x="{width/2}" y="{height-8}" text-anchor="middle" class="edupro-axis">{escape(x_col)}</text>'
        f'<text x="14" y="{height/2}" transform="rotate(-90 14 {height/2})" text-anchor="middle" class="edupro-axis">{escape(y_col)}</text>'
        f'<text x="{left}" y="{height-30}" class="edupro-tick">{x_min:.2f}</text>'
        f'<text x="{width-right}" y="{height-30}" text-anchor="end" class="edupro-tick">{x_max:.2f}</text>'
        f'<text x="{left-8}" y="{height-bottom}" text-anchor="end" class="edupro-tick">{y_min:.2f}</text>'
        f'<text x="{left-8}" y="{top+4}" text-anchor="end" class="edupro-tick">{y_max:.2f}</text>'
        f'</svg></div>'
    )
    st.markdown(svg, unsafe_allow_html=True)


def render_heatmap(frame, title, vmin=1.0, vmax=5.0):
    """Render a rating heatmap with CSS colors, avoiding matplotlib-backed Styler."""
    if frame.empty:
        st.info("No cells match the current filters.")
        return
    headers = ["Category"] + [str(col) for col in frame.columns]
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for index, row in frame.iterrows():
        cells = [f"<th>{escape(str(index))}</th>"]
        for value in row:
            if pd.isna(value):
                cells.append('<td style="text-align:center;color:#98A2B3">-</td>')
                continue
            ratio = max(0.0, min(1.0, (float(value) - vmin) / (vmax - vmin)))
            if ratio < 0.5:
                local = ratio * 2
                red, green = 220, int(145 + 80 * local)
            else:
                local = (ratio - 0.5) * 2
                red, green = int(220 - 105 * local), 205
            bg = f"rgb({red},{green},100)"
            cells.append(f'<td style="background:{bg};text-align:center;font-weight:600">{float(value):.2f}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    html = f'<div class="edupro-chart"><div class="edupro-chart-title">{escape(title)}</div><table><thead><tr>{header_html}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)


default_path = Path(__file__).with_name("EduPro Online Platform.xlsx")
st.markdown(
    """
    <style>
    .edupro-chart {border:1px solid #E4E7EC; border-radius:8px; padding:12px 14px; margin:8px 0 14px; background:#FFFFFF;}
    .edupro-chart-title {font-weight:600; color:#0B2545; margin-bottom:10px;}
    .edupro-bar-row {display:flex; align-items:center; gap:8px; margin:7px 0; font-size:0.9rem;}
    .edupro-bar-label {width:125px; color:#344054; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
    .edupro-bar-track {flex:1; height:12px; background:#F2F4F7; border-radius:6px; overflow:hidden;}
    .edupro-bar-fill {display:block; height:100%; background:#2E74B5; border-radius:6px;}
    .edupro-bar-value {width:54px; text-align:right; color:#475467;}
    .edupro-svg {width:100%; height:auto;}
    .edupro-axis {font-size:12px; fill:#475467;}
    .edupro-tick {font-size:11px; fill:#667085;}
    table {width:100%; border-collapse:collapse; margin:8px 0 14px; font-size:0.9rem;}
    th {background:#F2F4F7; color:#0B2545; font-weight:600; text-align:left; padding:7px 8px; border:1px solid #D0D5DD;}
    td {padding:7px 8px; border:1px solid #E4E7EC; color:#344054;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("EduPro Instructor Performance & Course Quality")
st.caption("Assignment-level analytics for teaching quality, course ratings, experience, and enrollment concentration")

with st.sidebar:
    st.header("Controls")
    upload = st.file_uploader("Upload EduPro workbook", type=["xlsx"])
    source = upload if upload is not None else (default_path if default_path.exists() else None)
    if source is None:
        st.info("Upload the provided 'EduPro Online Platform.xlsx' workbook to begin.")
        st.stop()
    st.caption("Source: uploaded workbook" if upload is not None else "Source: bundled project workbook")

try:
    users, teachers, courses, transactions, joined = load_workbook(source)
except Exception as exc:
    st.error(f"Could not load workbook: {exc}")
    st.stop()

teacher_summary = make_teacher_summary(joined)

with st.sidebar:
    st.divider()
    expertise_options = sorted(teacher_summary["Expertise"].dropna().unique())
    category_options = sorted(courses["CourseCategory"].dropna().unique())
    level_options = sorted(courses["CourseLevel"].dropna().unique())
    selected_expertise = st.multiselect("Instructor expertise", expertise_options)
    selected_categories = st.multiselect("Course categories", category_options)
    selected_levels = st.multiselect("Course levels", level_options)
    rating_min, rating_max = st.slider("Teacher rating range", 0.0, 5.0, (0.0, 5.0), 0.05)

filtered_joined = joined.copy()
if selected_expertise:
    filtered_joined = filtered_joined[filtered_joined["Expertise"].isin(selected_expertise)]
if selected_categories:
    filtered_joined = filtered_joined[filtered_joined["CourseCategory"].isin(selected_categories)]
if selected_levels:
    filtered_joined = filtered_joined[filtered_joined["CourseLevel"].isin(selected_levels)]
filtered_summary = make_teacher_summary(filtered_joined)
filtered_summary = filtered_summary[filtered_summary["TeacherRating"].between(rating_min, rating_max)]

tab_overview, tab_leaderboard, tab_course, tab_experience, tab_audit = st.tabs(
    ["Overview", "Instructor leaderboard", "Course quality", "Experience & impact", "Data audit"]
)

with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Average teacher rating", fmt(teachers["TeacherRating"].mean()))
    c2.metric("Average course rating", fmt(courses["CourseRating"].mean()))
    c3.metric("Transactions / enrollments", f"{len(transactions):,}")
    c4.metric("Unique learners", f"{transactions['UserID'].nunique():,}")

    st.subheader("Platform snapshot")
    left, right = st.columns(2)
    with left:
        teacher_dist = pd.cut(
            teachers["TeacherRating"],
            bins=[0, 2, 3, 4, 5.01],
            labels=["<2.0", "2.0–<3.0", "3.0–<4.0", "4.0+"],
        ).value_counts().sort_index().rename("Instructors")
        render_bar_chart(teacher_dist, "Instructor rating distribution", value_format="count")
        st.caption("Instructor rating distribution")
    with right:
        course_dist = pd.cut(
            courses["CourseRating"],
            bins=[0, 2, 3, 4, 5.01],
            labels=["<2.0", "2.0–<3.0", "3.0–<4.0", "4.0+"],
        ).value_counts().sort_index().rename("Courses")
        render_bar_chart(course_dist, "Course rating distribution", value_format="count")
        st.caption("Course rating distribution")

    st.info(
        "Interpretation: teacher experience is moderately associated with teacher ratings, "
        "but teacher ratings and assigned course ratings are effectively uncorrelated in this dataset. "
        "Use the relationship as descriptive evidence, not proof of causation."
    )

with tab_leaderboard:
    st.subheader("Instructor performance leaderboard")
    min_enrollments = st.slider("Minimum observed enrollments", 0, int(max(1, teacher_summary["Enrollments"].max())), 0, 10)
    leaderboard = filtered_summary[filtered_summary["Enrollments"] >= min_enrollments].copy()
    leaderboard = leaderboard.sort_values(["TeacherRating", "AvgAssignedCourseRating", "Enrollments"], ascending=False)
    display_cols = [
        "TeacherName", "Expertise", "YearsOfExperience", "TeacherRating", "RatingTier",
        "AvgAssignedCourseRating", "ConsistencyIndex", "Enrollments", "UniqueLearners", "UniqueCourses",
    ]
    render_table(
        leaderboard[display_cols].rename(
            columns={
                "TeacherName": "Instructor", "YearsOfExperience": "Experience (yrs)", "TeacherRating": "Teacher rating",
                "RatingTier": "Tier", "AvgAssignedCourseRating": "Avg assigned course rating",
                "ConsistencyIndex": "Consistency index", "Enrollments": "Enrollments",
                "UniqueLearners": "Unique learners", "UniqueCourses": "Unique courses",
            }
        ).round({"Teacher rating": 2, "Avg assigned course rating": 2, "Consistency index": 1}),
        index=False,
    )
    if not leaderboard.empty:
        chart_data = leaderboard[["TeacherRating", "AvgAssignedCourseRating", "Enrollments", "TeacherName"]].copy()
        chart_data["Label"] = chart_data["TeacherName"] + " (" + chart_data["Enrollments"].astype(str) + ")"
        render_scatter(chart_data, "TeacherRating", "AvgAssignedCourseRating", "Teacher rating vs assigned course rating", size_col="Enrollments")
        st.caption("Bubble size represents observed enrollments; each transaction is an observed teacher-course assignment.")

with tab_course:
    st.subheader("Course quality by category and level")
    course_view = courses.copy()
    if selected_categories:
        course_view = course_view[course_view["CourseCategory"].isin(selected_categories)]
    if selected_levels:
        course_view = course_view[course_view["CourseLevel"].isin(selected_levels)]
    category_summary = (
        course_view.groupby("CourseCategory", as_index=True)["CourseRating"]
        .agg(Courses="count", AvgRating="mean", RatingSD="std")
        .sort_values("AvgRating", ascending=False)
    )
    left, right = st.columns([1.1, 1])
    with left:
        render_bar_chart(category_summary["AvgRating"], "Average course rating by category")
        st.caption("Average course rating by category")
    with right:
        heatmap = course_view.pivot_table(index="CourseCategory", columns="CourseLevel", values="CourseRating", aggfunc="mean")
        render_heatmap(heatmap, "Average rating by category and level")
        st.caption("Average rating heatmap: green is higher, red is lower")
    render_table(
        category_summary.reset_index().rename(columns={"CourseCategory": "Category", "Courses": "Courses", "AvgRating": "Avg rating", "RatingSD": "Rating SD"})
        .round({"Avg rating": 2, "Rating SD": 2}),
        index=False,
    )

with tab_experience:
    st.subheader("Experience vs performance")
    course_level = joined.drop_duplicates("CourseID")
    corr_exp_teacher = correlation(teachers["YearsOfExperience"], teachers["TeacherRating"])
    corr_exp_course = correlation(course_level["YearsOfExperience"], course_level["CourseRating"])
    corr_teacher_course = correlation(joined["TeacherRating"], joined["CourseRating"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Experience → teacher rating", fmt(corr_exp_teacher, 3))
    m2.metric("Experience → course rating", fmt(corr_exp_course, 3))
    m3.metric("Teacher rating → course rating", fmt(corr_teacher_course, 3))
    st.caption("Pearson correlation. Course-level experience-to-course rating uses one record per course; teacher-course association is assignment-weighted.")

    scatter = teachers[["YearsOfExperience", "TeacherRating", "TeacherName"]].copy()
    render_scatter(scatter, "YearsOfExperience", "TeacherRating", "Experience vs teacher rating")
    st.caption("Each point is an instructor. A trend exists for experience and teacher rating, while the course-rating linkage is weak.")

    tier_summary = (
        teacher_summary.groupby("RatingTier", observed=False)
        .agg(Instructors=("TeacherID", "nunique"), Enrollments=("Enrollments", "sum"), AvgCourseRating=("AvgAssignedCourseRating", "mean"))
        .reset_index()
    )
    tier_summary["InstructorShare"] = tier_summary["Instructors"] / tier_summary["Instructors"].sum()
    tier_summary["EnrollmentShare"] = tier_summary["Enrollments"] / tier_summary["Enrollments"].sum()
    tier_display = tier_summary.copy()
    tier_display["AvgCourseRating"] = tier_display["AvgCourseRating"].round(2)
    tier_display["InstructorShare"] = (tier_display["InstructorShare"] * 100).round(1).astype(str) + "%"
    tier_display["EnrollmentShare"] = (tier_display["EnrollmentShare"] * 100).round(1).astype(str) + "%"
    render_table(tier_display, index=False)
    st.caption("High-rated instructors represent a smaller share of instructors but a disproportionately large share of observed enrollments.")

with tab_audit:
    st.subheader("Data audit and interpretation notes")
    audit = pd.DataFrame(
        {
            "Sheet": ["Users", "Teachers", "Courses", "Transactions"],
            "Rows": [len(users), len(teachers), len(courses), len(transactions)],
            "Duplicate rows": [int(users.duplicated().sum()), int(teachers.duplicated().sum()), int(courses.duplicated().sum()), int(transactions.duplicated().sum())],
            "Missing values": [int(users.isna().sum().sum()), int(teachers.isna().sum().sum()), int(courses.isna().sum().sum()), int(transactions.isna().sum().sum())],
        }
    )
    render_table(audit, index=False)
    pairs = joined[["CourseID", "TeacherID"]].drop_duplicates()
    p1, p2, p3 = st.columns(3)
    p1.metric("Teacher-course pairs", f"{len(pairs):,}")
    p2.metric("Avg teachers per course", fmt(pairs.groupby("CourseID")["TeacherID"].nunique().mean(), 1))
    p3.metric("All keys mapped", "Yes" if joined[["TeacherName", "CourseName"]].notna().all().all() else "No")
    st.markdown(
        "**Metric definitions**  \n"
        "• Consistency index = 100 × (1 − course-rating SD / 4), clipped at zero; higher means more stable assigned-course ratings.  \n"
        "• Rating tiers: Low < 3.0, Mid 3.0–< 4.0, High ≥ 4.0.  \n"
        "• Enrollments are transaction rows; unique learners use distinct UserID values.  \n"
        "• User email fields are not surfaced by the dashboard."
    )
    st.warning(
        "Because the transaction table contains the TeacherID assignment and the Courses table does not contain an author field, "
        "course ratings are interpreted as ratings observed alongside each instructor assignment. "
        "Confirm the business meaning of TeacherID before using this for instructor accountability decisions."
    )
