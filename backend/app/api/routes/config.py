from typing import List
from fastapi import APIRouter, HTTPException
from app.api.deps import SessionDep, CurrentUser
from app.schemas.config import (
    ConfigCategoryGroup, ConfigUpdatePayload, AuditLogItem, ExportImportPayload
)
from app.services.config_service import config_service

router = APIRouter(prefix="/api/config", tags=["System Configuration & AI Rules"])


@router.get("", response_model=ConfigCategoryGroup)
def get_configurations(db: SessionDep, current_user: CurrentUser):
    """Get all system configurations grouped by category."""
    return config_service.get_grouped_configs(db)


@router.patch("")
def update_configurations(
    payload: ConfigUpdatePayload,
    db: SessionDep,
    current_user: CurrentUser,
):
    """Batch update configuration settings and record audit log entries."""
    if not payload.settings:
        raise HTTPException(400, "Settings payload cannot be empty")

    updated_count = config_service.update_configs(
        db,
        payload.settings,
        user_email=getattr(current_user, 'email', 'admin@antigravity.ai'),
    )
    return {"message": f"Successfully updated {updated_count} configuration parameters"}


@router.get("/audit-logs", response_model=List[AuditLogItem])
def get_config_audit_logs(
    db: SessionDep,
    current_user: CurrentUser,
    limit: int = 100,
):
    """Get audit trail history of configuration modifications."""
    return config_service.get_audit_logs(db, limit=limit)


@router.post("/export", response_model=ExportImportPayload)
def export_configuration(db: SessionDep, current_user: CurrentUser):
    """Export complete system configuration dictionary as JSON."""
    return config_service.export_config(db)


@router.post("/import")
def import_configuration(
    payload: ExportImportPayload,
    db: SessionDep,
    current_user: CurrentUser,
):
    """Import and apply system configuration dictionary from JSON."""
    count = config_service.import_config(
        db,
        payload.model_dump(),
        user_email=getattr(current_user, 'email', 'admin@antigravity.ai'),
    )
    return {"message": f"Successfully imported configuration ({count} settings updated)"}


@router.post("/reset")
def reset_configuration_defaults(db: SessionDep, current_user: CurrentUser):
    """Reset all system configurations to factory defaults."""
    count = config_service.reset_to_defaults(
        db,
        user_email=getattr(current_user, 'email', 'admin@antigravity.ai'),
    )
    return {"message": f"Configurations reset to factory defaults ({count} settings reset)"}
