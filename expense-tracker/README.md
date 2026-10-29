# Expense Tracker

A command-line expense tracker built with Python and SQLite (standard library only).

## Features
add / list / delete expenses, filter by category or month, per-category summary, CSV export.

## Usage
    python -m expense_tracker add 250 food --note "lunch" --date 2026-10-05
    python -m expense_tracker add 1200 travel
    python -m expense_tracker list --category food
    python -m expense_tracker summary --month 2026-10
    python -m expense_tracker delete 1
    python -m expense_tracker export expenses.csv

## Tests
    pip install -r requirements.txt
    pytest

See `docs/ARCHITECTURE.md` for design details.
