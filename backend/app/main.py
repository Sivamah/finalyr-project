from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, providers, dashboard, orchestration, simulation
from app.api.routes import xai, notifications, drivers, config, playback, dmfe_v2, dmfe_engine
from app.core.config import settings
from contextlib import asynccontextmanager
from app.db.database import engine, Base, SessionLocal
from app.db.models import User
from app.core.security import get_password_hash
from app.core.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware
from app.db.database import sync_schema_columns

@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_schema_columns()  # idempotent legacy dev-DB column sync (SQLite only)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@aiorch.com").first()
        if not admin:
            admin = User(
                email="admin@aiorch.com",
                full_name="Platform Admin",
                password_hash=get_password_hash("admin123"),
                role="Admin",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()

    try:
        from app.services.driver_service import driver_service
        driver_service.seed_initial_data_if_needed(db)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("driver/vehicle seed failed")

    # Release trips stuck in Planned/Active (e.g. from a previous server run).
    # Without this, their drivers/vehicles stay Busy forever and the DMFE
    # driver-availability gate rejects every batch (Gate E starvation).
    try:
        from app.dmfe.driver_selection import complete_stale_trips
        db = SessionLocal()
        try:
            complete_stale_trips(db, max_age_min=30.0)
        finally:
            db.close()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("stale-trip cleanup failed: %s", exc)
    yield

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description="AI Orchestration Platform — Admin-Only Transportation & Delivery Optimization Engine",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,          prefix="/api/auth",          tags=["Authentication"])
app.include_router(providers.router,     prefix="/api/providers",     tags=["Providers"])
app.include_router(dashboard.router,     prefix="/api/dashboard",     tags=["Dashboard"])
app.include_router(orchestration.router, prefix="/api/orchestration", tags=["Orchestration"])
app.include_router(simulation.router,    prefix="/api/simulation",    tags=["Simulation"])
app.include_router(xai.router,           prefix="/api/xai",           tags=["Explainable AI"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications & Activity Center"])
app.include_router(drivers.router,                                     tags=["Driver & Vehicle Management"])
app.include_router(config.router,                                     tags=["System Configuration & AI Rules"])
app.include_router(playback.router,                                   tags=["Simulation Playback & Scenario Testing"])
app.include_router(dmfe_v2.router,                                    tags=["DMFE"])
app.include_router(dmfe_engine.router,                                tags=["DMFE Engine"])

@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}
