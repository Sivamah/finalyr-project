from sqlalchemy.orm import Session
from app.db import models
from app.services.websocket_manager import manager
import asyncio

async def notify_user(db: Session, user_id: int, title: str, message: str, notification_type: str = "INFO"):
    """
    Creates a notification in the database and sends it in real-time if the user is connected.
    """
    # 1. Save to DB
    notification = models.Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # 2. Send via WebSocket
    payload = {
        "event": "NOTIFICATION",
        "data": {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "created_at": notification.created_at.isoformat(),
            "is_read": False
        }
    }
    await manager.send_personal_message(payload, user_id)
    return notification
