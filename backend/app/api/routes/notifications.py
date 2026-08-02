from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from app.api.deps import SessionDep, CurrentUser
from app.schemas.notification import NotificationListResponse, NotificationStats, ActivityTimelineItem
from app.services.notification_service import notification_service

# NOTE: No prefix here — main.py registers this router with prefix="/api/notifications"
router = APIRouter(tags=["Notifications & Activity Center"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    db: SessionDep,
    current_user: CurrentUser,
    category: Optional[str] = None,
    read_status: Optional[str] = None,
    search: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 100,
):
    """Get list of notifications matching category, read status, search keywords, or date."""
    return notification_service.get_notifications(
        db,
        category=category,
        read_status=read_status,
        search=search,
        date=date,
        limit=limit,
    )


@router.get("/stats", response_model=NotificationStats)
def get_notification_stats(
    db: SessionDep,
    current_user: CurrentUser,
):
    """Get aggregate notification metrics (total, unread, today activities, warnings, errors)."""
    return notification_service.get_stats(db)


@router.get("/timeline", response_model=List[ActivityTimelineItem])
def get_activity_timeline(
    db: SessionDep,
    current_user: CurrentUser,
    limit: int = 100,
):
    """Get chronological system event activity timeline."""
    return notification_service.get_activity_timeline(db, limit=limit)


@router.patch("/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    db: SessionDep,
    current_user: CurrentUser,
):
    """Mark a single notification as read."""
    success = notification_service.mark_as_read(db, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router.patch("/read-all")
def mark_all_notifications_as_read(
    db: SessionDep,
    current_user: CurrentUser,
):
    """Mark all unread notifications as read."""
    count = notification_service.mark_all_as_read(db)
    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: SessionDep,
    current_user: CurrentUser,
):
    """Delete a single notification."""
    success = notification_service.delete_notification(db, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted successfully"}


@router.delete("/clear-all")
def clear_all_notifications(
    db: SessionDep,
    current_user: CurrentUser,
):
    """Delete all system notifications."""
    count = notification_service.clear_all(db)
    return {"message": f"Cleared {count} notifications"}
