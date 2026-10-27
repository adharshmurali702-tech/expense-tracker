# Pocket Ledger — Expense Tracker

A local personal finance app built with Python, SQLite, HTML and CSS. No third-party packages or API keys needed.

## Run
1. Install Python 3.10+ from https://www.python.org/downloads/ and select Add Python to PATH.
2. Extract the folder and open it in VS Code.
3. Open Terminal > New Terminal and run:

```powershell
py app.py
```

If `py` is unavailable, try `python app.py`. On macOS/Linux use `python3 app.py`.
The browser opens at http://127.0.0.1:8000. Keep the terminal open. Press Ctrl+C to stop.

## Features
- Add income and expenses with a date and category
- Edit and delete transactions, with deletion confirmation
- Filter by month or view all time
- Balance, income and expense summaries
- Category spending bars
- CSV export of the selected period
- Responsive interface and SQLite persistence

The app starts empty. Add your own records. Balance means income minus expenses for the selected period, not a bank account balance. Data stays in expenses.db beside app.py across restarts. Back up that file if needed.

## Understand the code
- app.py: server, HTML rendering, validation, database operations and CSV export
- style.css: responsive interface styling
- .gitignore: excludes financial data from Git
- tests.py: automated validation and integration checks

The browser submits HTML forms to Python. Python validates inputs, saves to SQLite using parameterized SQL, then redirects to the dashboard. Amounts are stored as integer paise to avoid rounding errors: ₹125.50 becomes 12550. Descriptions are escaped before rendering. A request token protects changes from cross-site form submissions.

## Test
Run `py tests.py`. Tests use a temporary database rather than your real records.

## GitHub
Create a repository named expense-tracker and upload the files, including .gitignore. Add screenshots after running the app. Never upload expenses.db or personal CSV exports. GitHub stores the source; GitHub Pages cannot run a Python server.

Suggested description: A Python and SQLite expense tracker with monthly summaries, category charts, and CSV export.

## Make it your own
1. Trace a saved form through validate(), SQL INSERT and page().
2. Add a category in CATEGORIES.
3. Explain why amounts use integer paise.
4. Add a monthly budget feature.
5. Take screenshots and describe your own changes in this README.

## Scope
A single-user local learning project. No accounts, bank connection or cloud sync. The Python standard-library HTTP server is for local use; do not expose this app to the internet as-is.
