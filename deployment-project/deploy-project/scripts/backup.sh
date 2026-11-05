#!/usr/bin/env bash
# Daily backup of the SQLite database using SQLite's safe online backup.
# Cron example:  0 2 * * * /opt/expense-tracker/scripts/backup.sh
set -euo pipefail
DB="${DB_PATH:-/data/expenses.db}"; DEST="${BACKUP_DIR:-/backups}"; KEEP_DAYS=14
mkdir -p "$DEST"
OUT="$DEST/expenses-$(date +%Y%m%d-%H%M%S).db"
python3 -c "import sqlite3,sys; s=sqlite3.connect('$DB'); d=sqlite3.connect('$OUT'); s.backup(d); d.close(); s.close()"
find "$DEST" -name 'expenses-*.db' -mtime +$KEEP_DAYS -delete
echo "Backup written to $OUT"
