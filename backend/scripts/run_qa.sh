#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/run_qa.sh  —  launch the backend against an isolated QA database
#
# WHY THIS EXISTS
# ───────────────
# The QA database (qa_test.db) is intentionally separate from the development
# database (dmfe_dev.db).  The wrong pattern is to edit backend/.env directly,
# because a file edit outlives a crashed process and silently poisons the next
# normal dev boot — exactly the bug this script was written to prevent.
#
# HOW IT WORKS
# ────────────
# This script exports DATABASE_URL as a PROCESS environment variable before
# launching uvicorn.  The override dies when the script exits or is killed;
# no file is written, no stale override is left behind.  The .env file is
# never touched.
#
# USAGE
# ─────
#   cd backend
#   bash scripts/run_qa.sh                  # default QA DB (qa_test.db)
#   DATABASE_URL=sqlite:///./my.db bash scripts/run_qa.sh   # override
#
# BEFORE/AFTER GUARANTEE
# ──────────────────────
# After this script exits (or is Ctrl-C'd), running the normal dev server:
#
#   cd backend && uvicorn app.main:app --reload
#
# …will use whatever DATABASE_URL is in .env (or the dmfe_dev.db fallback if
# .env has none).  No manual cleanup step required.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Use caller-supplied DATABASE_URL or default to QA SQLite file.
: "${DATABASE_URL:=sqlite:///${BACKEND_DIR}/qa_test.db}"

echo "▶  QA boot  |  DATABASE_URL=${DATABASE_URL}"
echo "   (override dies with this process — .env is NOT modified)"
echo ""

export DATABASE_URL

cd "$BACKEND_DIR"
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload \
     --log-level info "$@"
