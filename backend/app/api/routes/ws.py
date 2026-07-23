from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user_ws
from app.services.websocket_manager import manager
import json

router = APIRouter()

@router.websocket("/track")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for live tracking and notifications.
    Clients must pass ?token=... in the connection URL.
    """
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user.id)
    try:
        while True:
            # We don't expect much client->server data on WS in this simple design,
            # but we keep the loop alive to listen.
            data = await websocket.receive_text()
            # If needed, process incoming messages here (e.g. read receipts)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
