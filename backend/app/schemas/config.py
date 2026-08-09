from typing import Optional, Dict, Any
from pydantic import BaseModel


class ConfigItem(BaseModel):
    key: str
    category: str
    value: Any
    data_type: str = "string"
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ConfigCategoryGroup(BaseModel):
    simulation: Dict[str, Any] = {}
    provider: Dict[str, Any] = {}
    vehicle: Dict[str, Any] = {}
    ai_rules: Dict[str, Any] = {}
    preferences: Dict[str, Any] = {}


class ConfigUpdatePayload(BaseModel):
    settings: Dict[str, Any]  # {"simulation_speed": 3, "max_pickup_radius_km": 5.0, ...}


class AuditLogItem(BaseModel):
    id: int
    config_key: str
    category: str
    user_email: str
    previous_value: Optional[str] = None
    new_value: str
    created_at: str

    class Config:
        from_attributes = True


class ExportImportPayload(BaseModel):
    version: str = "1.0"
    exported_at: Optional[str] = None
    configurations: Dict[str, Any]
