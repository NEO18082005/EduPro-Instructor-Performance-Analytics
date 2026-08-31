# EduPro deployment guide

## GitHub

From PowerShell, inside this project folder:

```powershell
git init
git add app.py requirements.txt README.md DEPLOYMENT.md .gitignore "EduPro Online Platform.xlsx"
git commit -m "Add EduPro instructor performance dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repository>.git
git push -u origin main
```

Do not commit passwords, API keys, or other secrets. The workbook contains a Users sheet with email addresses; use the supplied dataset only in a private repository unless those fields have been removed or the data owner has approved publication.

## Streamlit Community Cloud

1. Create or select the GitHub repository.
2. In Streamlit Community Cloud, choose **New app**.
3. Select the repository, branch `main`, and file `app.py`.
4. Deploy. Streamlit will install the packages in `requirements.txt`.
5. The dashboard loads the bundled workbook automatically. Users can also upload an `.xlsx` file with the required four sheet names.

## Deployment notes

- The app intentionally uses HTML/SVG visuals and HTML tables instead of Streamlit's Arrow-backed dataframe/chart components. This avoids the `pyarrow` DLL issue on locked-down Windows machines.
- No secrets or external services are required.
- The source data model should be reviewed before using instructor results for accountability: Transactions contains TeacherID, while Courses does not contain a single author/owner field.
