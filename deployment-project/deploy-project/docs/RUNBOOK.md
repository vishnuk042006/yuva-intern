# Operations Runbook

## Reading logs
Each line looks like: `time level=INFO logger=expense_tracker msg=POST /expenses 201 3.2ms`
- Errors only: `docker compose -f docker-compose.prod.yml logs app | grep level=ERROR`
- Slow requests: look for large millisecond values at the end of the line.

## Metrics to watch
`GET /metrics` returns total requests, errors and counts per status code.
Alert when the error ratio (errors / requests) rises above about 5%.

## Common problems
| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `/health` fails | container down or DB volume not writable | check `docker ps`, logs, volume permissions |
| 401 on POST | wrong or missing `X-API-Key` | send the key configured in the environment |
| 500 errors | bug or database problem | read the traceback in logs, roll back if urgent |
| "database is locked" | heavy concurrent writes | reduce workers or move to PostgreSQL |

## Rollback
`scripts/rollback.sh prod` restores the previously deployed image. `deploy.sh`
does this automatically if the smoke test fails.

## Backup and restore
Backup runs daily via cron (`scripts/backup.sh`, 14 days kept).
Restore: stop the app, copy the chosen backup to the data volume as `expenses.db`, start the app.
