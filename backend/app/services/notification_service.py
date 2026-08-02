import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import func, String
from sqlalchemy.orm import Session
from app.db.models import SystemNotification

logger = logging.getLogger(__name__)


def log_system_notification(
    db: Session,
    title: str,
    description: str = "",
    category: str = "Information",  # Information / Success / Warning / Error
    event_type: str = "simulation_state",
    request_id: Optional[int] = None,
    provider_name: Optional[str] = None,
) -> Optional[SystemNotification]:
    """Helper function to record a system notification in DB."""
    try:
        notif = SystemNotification(
            title=title,
            description=description,
            category=category,
            event_type=event_type,
            request_id=request_id,
            provider_name=provider_name,
            is_read=False,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif
    except Exception as exc:
        logger.warning("Failed to log system notification: %s", exc)
        db.rollback()
        return None


class NotificationService:
    """Read & management service for system notifications and activity logs."""

    def get_notifications(
        self,
        db: Session,
        category: Optional[str] = None,
        read_status: Optional[str] = None,
        search: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        query = db.query(SystemNotification)

        if category and category.lower() != "all":
            query = query.filter(func.lower(SystemNotification.category) == category.lower())

        if read_status and read_status.lower() != "all":
            if read_status.lower() == "unread":
                query = query.filter(SystemNotification.is_read == False)
            elif read_status.lower() == "read":
                query = query.filter(SystemNotification.is_read == True)

        if date and date.lower() == "today":
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(SystemNotification.created_at >= today_start)

        if search:
            s_lower = search.lower()
            query = query.filter(
                (func.lower(SystemNotification.title).contains(s_lower)) |
                (func.lower(SystemNotification.description).contains(s_lower)) |
                (func.lower(SystemNotification.provider_name).contains(s_lower)) |
                (func.cast(SystemNotification.request_id, String).contains(s_lower))
            )

        items = query.order_by(SystemNotification.created_at.desc()).limit(limit).all()
        unread_count = db.query(SystemNotification).filter(SystemNotification.is_read == False).count()

        formatted_items = []
        for n in items:
            c_at = n.created_at or datetime.now(timezone.utc)
            if c_at.tzinfo is None:
                c_at = c_at.replace(tzinfo=timezone.utc)
            formatted_items.append({
                "id": n.id,
                "title": n.title,
                "description": n.description or "",
                "category": n.category or "Information",
                "event_type": n.event_type or "simulation_state",
                "request_id": n.request_id,
                "provider_name": n.provider_name,
                "is_read": bool(n.is_read),
                "created_at": c_at.isoformat(),
            })

        return {
            "total": len(formatted_items),
            "unread": unread_count,
            "items": formatted_items,
        }

    def get_stats(self, db: Session) -> Dict[str, int]:
        total = db.query(SystemNotification).count()
        unread = db.query(SystemNotification).filter(SystemNotification.is_read == False).count()
        
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(SystemNotification).filter(SystemNotification.created_at >= today_start).count()
        
        warnings = db.query(SystemNotification).filter(func.lower(SystemNotification.category) == "warning").count()
        errors = db.query(SystemNotification).filter(func.lower(SystemNotification.category) == "error").count()

        return {
            "total_notifications": total,
            "unread_notifications": unread,
            "today_activities": today_count,
            "warnings_count": warnings,
            "errors_count": errors,
        }

    def get_activity_timeline(self, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        items = db.query(SystemNotification).order_by(SystemNotification.created_at.desc()).limit(limit).all()
        result = []
        for n in items:
            c_at = n.created_at or datetime.now(timezone.utc)
            if c_at.tzinfo is None:
                c_at = c_at.replace(tzinfo=timezone.utc)
            time_str = c_at.strftime("%I:%M %p")
            result.append({
                "id": n.id,
                "time_str": time_str,
                "title": n.title,
                "description": n.description or "",
                "category": n.category or "Information",
                "request_id": n.request_id,
                "created_at": c_at.isoformat(),
            })
        return result

    def mark_as_read(self, db: Session, notification_id: int) -> bool:
        n = db.query(SystemNotification).filter(SystemNotification.id == notification_id).first()
        if n:
            n.is_read = True
            db.commit()
            return True
        return False

    def mark_all_as_read(self, db: Session) -> int:
        count = db.query(SystemNotification).filter(SystemNotification.is_read == False).update({"is_read": True})
        db.commit()
        return count

    def delete_notification(self, db: Session, notification_id: int) -> bool:
        n = db.query(SystemNotification).filter(SystemNotification.id == notification_id).first()
        if n:
            db.delete(n)
            db.commit()
            return True
        return False

    def clear_all(self, db: Session) -> int:
        count = db.query(SystemNotification).delete()
        db.commit()
        return count


notification_service = NotificationService()
