# Deployment Guide

## 1. Production-readiness checklist
- [x] Config from environment variables, no secrets in code (`.env.example`)
- [x] Dependencies pinned in `requirements.txt`
- [x] Input validation, request size limit, API key on write endpoints
- [x] Parameterised SQL queries; non-root container user
- [x] Health check (`/health`) and metrics (`/metrics`) endpoints
- [x] Structured logging to stdout; log rotation in compose file
- [x] Automated tests run in CI before anything is built
- [x] Backups (`scripts/backup.sh`) and rollback (`scripts/rollback.sh`)

## 2. Environments
| | Staging | Production |
|-|---------|------------|
| Compose file | `docker-compose.staging.yml` | `docker-compose.prod.yml` |
| Port | 8001 | 8000 |
| Log level | DEBUG | INFO |
| Data | own volume | own volume |
Staging uses the same image as production so what is tested is what ships.

## 3. Pipeline (`.github/workflows/ci-cd.yml`)
push -> run tests -> build Docker image tagged with commit SHA -> push to registry
-> manual approval -> deploy to production.

## 4. Deploy steps
1. `docker build -t expense-tracker:v1 .`
2. Create `.env` from `.env.example` and set a strong `API_KEY`.
3. Staging: `API_KEY=... scripts/deploy.sh staging v1`
4. Test staging thoroughly (smoke test runs automatically; also try add/list/summary by hand).
5. Production: `API_KEY=... scripts/deploy.sh prod v1`
6. Watch logs: `docker compose -f docker-compose.prod.yml logs -f`

## 5. Put it behind HTTPS
Use a reverse proxy (Nginx, Caddy) or a platform that provides TLS (Render, Railway,
Fly.io). Do not expose port 8000 directly to the internet.

## 6. Example requests
    curl http://localhost:8000/health
    curl -X POST http://localhost:8000/expenses -H "X-API-Key: $API_KEY" \
         -H "Content-Type: application/json" -d '{"amount": 250, "category": "food"}'
    curl "http://localhost:8000/summary?month=2026-11"
