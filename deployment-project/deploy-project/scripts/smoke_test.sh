#!/usr/bin/env bash
# Usage: scripts/smoke_test.sh http://localhost:8001
set -euo pipefail
URL="${1:?base url required}"
echo "Checking $URL/health"
curl -fsS "$URL/health" | grep -q '"status": "ok"' && echo "health OK"
curl -fsS "$URL/expenses" > /dev/null && echo "list OK"
curl -fsS "$URL/summary"  > /dev/null && echo "summary OK"
echo "Smoke test passed"
