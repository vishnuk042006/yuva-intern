#!/usr/bin/env bash
# Usage: scripts/deploy.sh <staging|prod> <image-tag>
# Keeps the previous tag so rollback.sh can restore it.
set -euo pipefail
ENVIRONMENT="${1:?staging or prod}"; TAG="${2:?image tag}"
FILE="docker-compose.${ENVIRONMENT}.yml"
PORT=$([ "$ENVIRONMENT" = "prod" ] && echo 8000 || echo 8001)

[ -f .current_tag_$ENVIRONMENT ] && cp .current_tag_$ENVIRONMENT .previous_tag_$ENVIRONMENT || true
export IMAGE="expense-tracker:${TAG}"
docker compose -f "$FILE" up -d
sleep 5
if scripts/smoke_test.sh "http://localhost:${PORT}"; then
  echo "$TAG" > .current_tag_$ENVIRONMENT
  echo "Deployed $TAG to $ENVIRONMENT"
else
  echo "Smoke test FAILED - rolling back"
  scripts/rollback.sh "$ENVIRONMENT"
  exit 1
fi
