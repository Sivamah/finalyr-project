import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.json_utils import json_loads
from app.db.models import SystemConfig, ConfigAuditLog
from app.dmfe.compatibility import clear_config_cache
from app.services.notification_service import log_system_notification

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DEFS = {
    # ── 1. Simulation Settings ──────────────────────────────────────────
    "simulation_speed": {"category": "simulation", "value": 3, "data_type": "int"},
    "max_queue_size": {"category": "simulation", "value": 500, "data_type": "int"},
    "simulation_duration": {"category": "simulation", "value": 60, "data_type": "int"},
    "auto_restart": {"category": "simulation", "value": True, "data_type": "bool"},
    "auto_cleanup": {"category": "simulation", "value": False, "data_type": "bool"},

    # ── 2. Provider Configuration ───────────────────────────────────────
    "provider_enabled_map": {"category": "provider", "value": {"1": True, "2": True, "3": True}, "data_type": "json"},
    "max_daily_capacity": {"category": "provider", "value": 1000, "data_type": "int"},
    "supported_services": {"category": "provider", "value": ["Ride", "Food", "Parcel"], "data_type": "json"},
    "provider_priority_map": {"category": "provider", "value": {"1": "High", "2": "Medium", "3": "Medium"}, "data_type": "json"},

    # ── 3. Vehicle Rules ────────────────────────────────────────────────
    "max_vehicle_capacity": {"category": "vehicle", "value": 6, "data_type": "int"},
    "max_route_distance_km": {"category": "vehicle", "value": 50.0, "data_type": "float"},
    "max_working_hours": {"category": "vehicle", "value": 8.0, "data_type": "float"},
    "maintenance_threshold_km": {"category": "vehicle", "value": 5000.0, "data_type": "float"},

    # ── 4. AI Rule Configurations (Store & Manage Only) ─────────────────
    "max_pickup_radius_km": {"category": "ai_rules", "value": 5.0, "data_type": "float"},
    "max_delivery_radius_km": {"category": "ai_rules", "value": 15.0, "data_type": "float"},
    "max_allowed_delay_min": {"category": "ai_rules", "value": 20.0, "data_type": "float"},
    "min_compatibility_score": {"category": "ai_rules", "value": 70.0, "data_type": "float"},
    "priority_weight": {"category": "ai_rules", "value": 0.35, "data_type": "float"},
    "distance_weight": {"category": "ai_rules", "value": 0.25, "data_type": "float"},
    "time_weight": {"category": "ai_rules", "value": 0.25, "data_type": "float"},
    "capacity_weight": {"category": "ai_rules", "value": 0.15, "data_type": "float"},

    # ── 5. System Preferences ───────────────────────────────────────────
    "theme": {"category": "preferences", "value": "Dark", "data_type": "string"},
    "language": {"category": "preferences", "value": "English", "data_type": "string"},
    "time_zone": {"category": "preferences", "value": "Asia/Kolkata (IST)", "data_type": "string"},
    "date_format": {"category": "preferences", "value": "YYYY-MM-DD", "data_type": "string"},
    "refresh_interval": {"category": "preferences", "value": 2.5, "data_type": "float"},
}


class ConfigService:
    """Service layer for system configurations, audit logging, and backup/restore."""

    def seed_defaults_if_needed(self, db: Session):
        """Ensure factory default configuration keys exist in DB."""
        try:
            existing_keys = {c.key for c in db.query(SystemConfig).all()}
            for key, info in DEFAULT_CONFIG_DEFS.items():
                if key not in existing_keys:
                    val_str = json.dumps(info["value"]) if info["data_type"] in ("json", "bool") or isinstance(info["value"], (dict, list)) else str(info["value"])
                    cfg = SystemConfig(
                        category=info["category"],
                        key=key,
                        value=val_str,
                        data_type=info["data_type"],
                    )
                    db.add(cfg)
            db.commit()
        except Exception as exc:
            logger.warning("seed_defaults_if_needed error: %s", exc)
            db.rollback()

    def _parse_val(self, val_str: str, data_type: str) -> Any:
        if data_type == "int":
            try:
                return int(val_str)
            except Exception:
                return 0
        elif data_type == "float":
            try:
                return float(val_str)
            except Exception:
                return 0.0
        elif data_type == "bool":
            return val_str.lower() in ("true", "1", "yes")
        elif data_type == "json":
            return json_loads(val_str, {})
        return val_str

    def get_grouped_configs(self, db: Session) -> Dict[str, Dict[str, Any]]:
        self.seed_defaults_if_needed(db)
        items = db.query(SystemConfig).all()

        grouped: Dict[str, Dict[str, Any]] = {
            "simulation": {},
            "provider": {},
            "vehicle": {},
            "ai_rules": {},
            "preferences": {},
        }

        for item in items:
            parsed = self._parse_val(item.value, item.data_type)
            cat = item.category if item.category in grouped else "preferences"
            grouped[cat][item.key] = parsed

        return grouped

    def update_configs(self, db: Session, settings: Dict[str, Any], user_email: str = "admin@antigravity.ai") -> int:
        self.seed_defaults_if_needed(db)
        updated_count = 0

        for key, new_val in settings.items():
            cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if not cfg:
                continue

            old_parsed = self._parse_val(cfg.value, cfg.data_type)
            if old_parsed == new_val:
                continue

            # Serialize new value
            if cfg.data_type in ("json", "bool") or isinstance(new_val, (dict, list, bool)):
                new_str = json.dumps(new_val)
            else:
                new_str = str(new_val)

            old_str = cfg.value
            cfg.value = new_str
            updated_count += 1

            # Log audit trail
            audit = ConfigAuditLog(
                config_key=key,
                category=cfg.category,
                user_email=user_email,
                previous_value=old_str,
                new_value=new_str,
            )
            db.add(audit)

        db.commit()

        if updated_count > 0:
            # Config values changed — drop the TTL caches so the new values
            # are seen immediately (not after the 15s `_CONFIG_CACHE_TTL`).
            clear_config_cache()
            log_system_notification(
                db,
                title="Configuration Updated",
                description=f"Updated {updated_count} system settings",
                category="Information",
                event_type="simulation_state",
            )

        return updated_count

    def get_audit_logs(self, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        logs = db.query(ConfigAuditLog).order_by(ConfigAuditLog.created_at.desc()).limit(limit).all()
        result = []
        for l in logs:
            c_at = l.created_at or datetime.now(timezone.utc)
            if c_at.tzinfo is None:
                c_at = c_at.replace(tzinfo=timezone.utc)

            result.append({
                "id": l.id,
                "config_key": l.config_key,
                "category": l.category,
                "user_email": l.user_email or "admin@antigravity.ai",
                "previous_value": l.previous_value or "N/A",
                "new_value": l.new_value,
                "created_at": c_at.strftime("%Y-%m-%d %I:%M:%S %p"),
            })
        return result

    def export_config(self, db: Session) -> Dict[str, Any]:
        grouped = self.get_grouped_configs(db)
        return {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "configurations": grouped,
        }

    def import_config(self, db: Session, payload: Dict[str, Any], user_email: str = "admin@antigravity.ai") -> int:
        configs_data = payload.get("configurations", {})
        flat_settings = {}
        for category, cat_dict in configs_data.items():
            if isinstance(cat_dict, dict):
                for k, v in cat_dict.items():
                    flat_settings[k] = v

        count = self.update_configs(db, flat_settings, user_email=user_email)
        log_system_notification(
            db,
            title="Configuration Imported",
            description=f"Imported JSON configuration ({count} settings updated)",
            category="Success",
            event_type="simulation_state",
        )
        return count

    def reset_to_defaults(self, db: Session, user_email: str = "admin@antigravity.ai") -> int:
        flat_defaults = {key: info["value"] for key, info in DEFAULT_CONFIG_DEFS.items()}
        count = self.update_configs(db, flat_defaults, user_email=user_email)
        log_system_notification(
            db,
            title="Factory Reset Configuration",
            description="System configurations reset to factory default parameters",
            category="Warning",
            event_type="simulation_state",
        )
        return count


config_service = ConfigService()
