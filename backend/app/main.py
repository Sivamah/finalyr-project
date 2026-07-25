from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, bookings, drivers, admin, dmfe, scheduler, routing, ws, notifications, tracking, analytics
from app.core.config import settings
from contextlib import asynccontextmanager
from app.db.database import engine, Base, SessionLocal
from app.db.models import User
from app.core.security import get_password_hash
from app.core.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables
    Base.metadata.create_all(bind=engine)
    
    # Seed demo users
    db = SessionLocal()
    try:
        demo_users = [
            {"email": "customer@test.com", "full_name": "Demo Customer", "password": "123456", "role": "Customer"},
            {"email": "driver@test.com", "full_name": "Demo Driver", "password": "123456", "role": "Driver"},
            {"email": "admin@test.com", "full_name": "Demo Admin", "password": "admin123", "role": "Admin"}
        ]
        
        for u in demo_users:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                new_user = User(
                    email=u["email"],
                    full_name=u["full_name"],
                    password_hash=get_password_hash(u["password"]),
                    role=u["role"],
                )
                db.add(new_user)
            else:
                # Update password just in case it was changed previously
                existing.password_hash = get_password_hash(u["password"])
                
        db.commit()
    finally:
        db.close()
    
    yield
    # Shutdown logic if any

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description=(
        "AI-Powered Unified Mobility and Delivery System — Final Production Build (Phase 9). "
        "Complete API suite for Ride, Food, Parcel, DMFE, Tracking, and Analytics."
    ),
    version="9.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Custom Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# CORS configuration
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,     prefix="/api/auth",     tags=["Authentication"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(drivers.router,  prefix="/api/drivers",  tags=["Drivers"])
app.include_router(admin.router,    prefix="/api/admin",    tags=["Admin"])
app.include_router(dmfe.router,     tags=["DMFE"])
app.include_router(scheduler.router, tags=["Scheduler"])
app.include_router(routing.router,  prefix="/api/routing",  tags=["Routing"])
app.include_router(ws.router,       prefix="/api/ws",       tags=["WebSockets"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(tracking.router, prefix="/api/tracking", tags=["Tracking"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "2.0.0"}
