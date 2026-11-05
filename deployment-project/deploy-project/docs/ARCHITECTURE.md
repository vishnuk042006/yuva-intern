# Architecture and Technical Guide

## Requirements
- Add, list, filter, delete expenses
- Totals per category, optionally per month
- Export to CSV; data must persist between runs
- Reject invalid input with clear messages

## Design: three layers
| Layer | File | Responsibility |
|-------|------|----------------|
| Presentation | `cli.py` | Parse arguments, print output, set exit code |
| Business | `service.py` | Validation rules, queries, CSV export |
| Data | `database.py` | SQLite connection and schema |

Each layer only talks to the one below it, so the CLI could be replaced by a web
API without touching business rules or the database code.

## Key decisions
- **SQLite** - zero setup, ships with Python, enough for a single-user tool.
- **Parameterised queries** everywhere to prevent SQL injection.
- **CHECK constraint** on amount plus service-level validation (defence in depth).
- **Indexes** on category and date, the two filter columns.
- **In-memory database** (`:memory:`) for fast, isolated tests.
- Categories are normalised to lowercase so "Food" and "food" are the same.

## Data flow
`cli.py` -> `service.add_expense()` (validate) -> `database` (INSERT) -> id returned -> CLI prints it.

## Extending
Add a new command in `cli.py`, put its logic in `service.py`, and add tests in `tests/`.
