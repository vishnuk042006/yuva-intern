# Expense Tracker - Deployment Edition

The Phase 3 Expense Tracker, extended to run in production: web API, Docker image,
staging and production configs, CI/CD pipeline, monitoring endpoints, backup and rollback.

## Run locally
    pip install -r requirements.txt
    pytest
    gunicorn wsgi:app --bind 0.0.0.0:8000

## Run with Docker
    docker build -t expense-tracker:v1 .
    docker run -p 8000:8000 -e API_KEY=secret -v data:/data expense-tracker:v1

## CLI (still available)
    python -m expense_tracker add 250 food

## Documentation
- `docs/DEPLOYMENT.md` - checklist, environments, pipeline, deploy steps
- `docs/RUNBOOK.md` - logs, metrics, troubleshooting, rollback, backups
- `docs/ARCHITECTURE.md` - application design
