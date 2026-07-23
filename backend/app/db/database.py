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

