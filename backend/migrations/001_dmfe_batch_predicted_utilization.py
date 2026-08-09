"""
Migration 001 — DMFEBatch.predicted_utilization_pct
===================================================
Adds the additive, nullable ``predicted_utilization_pct`` column (FLOAT,
DEFAULT 0.0) to ``dmfe_batches``.

Idempotent, dialect-aware (SQLite dev / PostgreSQL prod).  No Alembic is
used in this project; the ORM model change plus ``sync_schema_columns()``
at startup already migrates SQLite dev DBs, so this script exists for
manual/CI migration of existing environments.

Usage:
    python -m migrations.001_dmfe_batch_predicted_utilization
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text  # noqa: E402

from app.db.database import engine  # noqa: E402

TABLE = "dmfe_batches"
COLUMN = "predicted_utilization_pct"


def _has_column(conn) -> bool:
    if engine.dialect.name == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({TABLE})")).fetchall()
        return any(r[1] == COLUMN for r in rows)
    rows = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t"
        ),
        {"t": TABLE},
    ).fetchall()
    return any(r[0] == COLUMN for r in rows)


def main() -> None:
    with engine.begin() as conn:
        if TABLE not in inspect(engine).get_table_names():
            print(f"table {TABLE} missing — run create_all first")
            sys.exit(1)
        if _has_column(conn):
            print(f"{TABLE}.{COLUMN} already present — no-op")
            return
        ddl = (
            f"ALTER TABLE {TABLE} "
            f"ADD COLUMN {COLUMN} FLOAT DEFAULT 0.0"
        )
        conn.execute(text(ddl))
        print(f"added {TABLE}.{COLUMN} (FLOAT DEFAULT 0.0)")


if __name__ == "__main__":
    main()
