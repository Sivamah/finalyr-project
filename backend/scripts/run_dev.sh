#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/run_dev.sh  —  launch the backend against the standard dev database
#
# Use this instead of bare `uvicorn` to make the isolation guarantee explicit:
# it confirms the DATABASE_URL that will actually be used, so there are no
# surprises when .env has been left in an unusual state.
#
# USAGE
#   cd backend
#   bash scripts/run_dev.sh            # uses .env / defaults to dmfe_dev.db
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Resolve the database URL that pydantic-settings will pick up, so the
# operator can see it before the server boots.
if [ -f "${BACKEND_DIR}/.env" ]; then
    ENV_DB_URL=$(grep -E "^DATABASE_URL=" "${BACKEND_DIR}/.env" | cut -d= -f2- || true)
else
    ENV_DB_URL=""
fi

EFFECTIVE_DB="${ENV_DB_URL:-sqlite:///${BACKEND_DIR}/dmfe_dev.db (fallback — no DATABASE_URL in .env)}"

echo "▶  Dev boot  |  DATABASE_URL=${EFFECTIVE_DB}"
echo ""

# Warn loudly if the .env still points at the QA database
if echo "${EFFECTIVE_DB}" | grep -q "qa_test"; then
    echo "⚠  WARNING: .env points at qa_test.db — this is the QA database, not the dev database."
    echo "   Reset backend/.env to use DATABASE_URL=sqlite:///./dmfe_dev.db (or leave DATABASE_URL blank)"
    echo "   to use the default dev database.  Waiting 5 seconds before booting…"
    sleep 5
fi

cd "$BACKEND_DIR"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
     --log-level info "$@"
