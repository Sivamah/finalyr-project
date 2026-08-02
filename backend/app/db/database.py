from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Use DATABASE_URL if provided directly, otherwise build from POSTGRES settings
# Falls back to SQLite for development if no DB config is set
database_url = settings.SQLALCHEMY_DATABASE_URI

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    # For SQLite, we need connect_args to allow multi-threaded access
    **({"connect_args": {"check_same_thread": False}} if database_url.startswith("sqlite") else {})
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sync_schema_columns() -> None:
    """
    Idempotent schema sync for legacy development databases (SQLite only).

    Base.metadata.create_all() creates missing TABLES but never alters
    existing ones, so tables created by an older model version may lack
    columns.  This adds every column the ORM models declare that is missing
    from an existing table, using the model's column type and default.
    No-op for PostgreSQL (production databases are created fresh by
    create_all, so no drift can occur).
    """
    if not database_url.startswith("sqlite"):
        return

    from sqlalchemy import inspect, text
    from app.db.models import Base as AppBase  # noqa: F401 — registers all models

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in AppBase.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_cols:
                    continue

                ddl = (
                    f'ALTER TABLE "{table.name}" '
                    f'ADD COLUMN "{column.name}" '
                    f'{column.type.compile(engine.dialect)}'
                )
                default = column.default.arg if column.default is not None else None
                if default is not None and not callable(default):
                    if isinstance(default, str):
                        default = f"'{default}'"
                    ddl += f" DEFAULT {default}"
                conn.execute(text(ddl))

