#!/usr/bin/env bash
# Usage: scripts/rollback.sh <staging|prod>
set -euo pipefail
ENVIRONMENT="${1:?staging or prod}"
PREV=$(cat ".previous_tag_${ENVIRONMENT}" 2>/dev/null || true)
[ -z "$PREV" ] && { echo "No previous version recorded"; exit 1; }
export IMAGE="expense-tracker:${PREV}"
docker compose -f "docker-compose.${ENVIRONMENT}.yml" up -d
echo "$PREV" > ".current_tag_${ENVIRONMENT}"
echo "Rolled back $ENVIRONMENT to $PREV"
