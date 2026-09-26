import logging
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Security, WebSocket, WebSocketDisconnect, status, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..core.config import settings
from ..db.models import NotificationCreate, NotificationResponse, NotificationAck, DeviceStatus
from ..db.database import get_db
from ..services.connection_manager import manager
from ..services.notification_service import notification_service

logger = logging.getLogger("notification_server.api")
router = APIRouter()
security = HTTPBearer(auto_error=False)

# Producer Auth Dependency
async def verify_producer_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    request: Request = None
) -> str:
    """Validate Bearer token or X-API-Key header against configured API_KEYS."""
    api_key = None
    if credentials:
        api_key = credentials.credentials
    elif request and "x-api-key" in request.headers:
        api_key = request.headers["x-api-key"]
        
    if not api_key or api_key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key. Provide 'Authorization: Bearer <key>' or 'X-API-Key' header."
        )
    return api_key

# 1. Ingestion Endpoint
@router.post("/api/v1/notify", status_code=status.HTTP_201_CREATED)
async def post_notification(
    notification: NotificationCreate,
    api_key: str = Depends(verify_producer_api_key)
):
    """
    Ingest notification from external applications (App 1, App 2, App 3, etc.).
    Persists to SQLite and dispatches in real-time to active WebSocket clients.
    """
    result = await notification_service.create_notification(notification)
    return {
        "success": True,
        "notification_id": result["id"],
        "status": result["status"],
        "created_at": result["created_at"],
        "target_device": result["target_device"]
    }

# 2. Test Alert Generator
@router.post("/api/v1/test-alert")
async def trigger_test_alert(
    title: str = Query("Test Alert", description="Alert Title"),
    message: str = Query("This is a live test notification from the server.", description="Alert Message"),
    priority: str = Query("high", description="low, normal, high, critical"),
    source: str = Query("web-dashboard", description="Sender name"),
    target_device: Optional[str] = Query("all", description="Target device_id or 'all'"),
    api_key: str = Depends(verify_producer_api_key)
):
    """Trigger a mock notification for testing."""
    notif = NotificationCreate(
        source=source,
        title=title,
        message=message,
        priority=priority,
        category="test",
        target_device=target_device or "all"
    )
    return await notification_service.create_notification(notif)

# 3. List Notification History
@router.get("/api/v1/notifications")
async def list_notifications(
    limit: int = 50,
    offset: int = 0,
    source: Optional[str] = None,
    api_key: str = Depends(verify_producer_api_key)
):
    """List recent notifications."""
    async with get_db() as db:
        query = "SELECT * FROM notifications"
        params = []
        if source:
            query += " WHERE source = ?"
            params.append(source)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

# 4. List Devices
@router.get("/api/v1/devices")
async def list_devices(api_key: str = Depends(verify_producer_api_key)):
    """List all registered devices and online status."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM devices ORDER BY last_seen DESC;")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

# 5. Acknowledge Notifications
@router.post("/api/v1/notifications/ack")
async def acknowledge_notifications(
    ack: NotificationAck,
    api_key: str = Depends(verify_producer_api_key)
):
    await notification_service.acknowledge_notifications(ack.notification_ids, ack.device_id)
    return {"success": True, "acknowledged": len(ack.notification_ids)}

# 6. Persistent Client WebSocket Handshake & Stream
@router.websocket("/ws/connect")
async def websocket_client_connect(
    websocket: WebSocket,
    token: str = Query(..., description="Device authentication token"),
    device_id: str = Query(..., description="Unique client identifier (e.g. bala-laptop)"),
    device_name: Optional[str] = Query("Windows Client", description="Human readable device name"),
    version: Optional[str] = Query("1.0.0")
):
    """
    Persistent outbound WebSocket connection from your laptop client.
    Handles auth, registers device, catches up on pending alerts, and receives real-time pushes.
    """
    # Verify device authentication token
    if token != settings.DEVICE_AUTH_TOKEN:
        logger.warning(f"Rejected WS connection from {device_id}: Invalid token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid device token")
        return

    client_ip = websocket.client.host if websocket.client else "unknown"
    await manager.register_device(device_id, device_name, websocket, client_ip, version)

    try:
        # A. Handshake ACK
        await websocket.send_json({
            "type": "connection_established",
            "device_id": device_id,
            "message": "Connected to Notification Gateway"
        })

        # B. Catch-Up: Deliver any pending/offline notifications
        pending = await notification_service.get_pending_for_device(device_id)
        if pending:
            logger.info(f"Delivering {len(pending)} offline/pending notifications to {device_id}")
            for item in pending:
                await websocket.send_json({
                    "type": "notification",
                    "notification": item,
                    "offline_buffer": True
                })

        # C. Listen loop for client ACKs and Heartbeats
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "ack":
                notif_ids = data.get("notification_ids", [])
                if notif_ids:
                    await notification_service.acknowledge_notifications(notif_ids, device_id)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected gracefully: {device_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {device_id}: {e}")
    finally:
        await manager.disconnect_device(device_id, websocket)

# 7. Dashboard WebSocket
@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.register_dashboard(websocket)
    try:
        while True:
            # Keep open
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_dashboard(websocket)
    except Exception:
        await manager.disconnect_dashboard(websocket)
