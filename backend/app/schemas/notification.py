from typing import Optional, List
from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: int
    title: str
    description: str = ""
    category: str = "Information"       # Information / Success / Warning / Error
    event_type: str = "simulation_state"
    request_id: Optional[int] = None
    provider_name: Optional[str] = None
    is_read: bool = False
    created_at: str

    class Config:
        from_attributes = True


class NotificationStats(BaseModel):
    total_notifications: int = 0
    unread_notifications: int = 0
    today_activities: int = 0
    warnings_count: int = 0
    errors_count: int = 0


class ActivityTimelineItem(BaseModel):
    id: int
    time_str: str
    title: str
    description: str
    category: str
    request_id: Optional[int] = None
    created_at: str


class NotificationListResponse(BaseModel):
    total: int
    unread: int
    items: List[NotificationItem] = []
