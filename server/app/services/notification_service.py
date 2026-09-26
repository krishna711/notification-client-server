import uuid
import json
import logging
from datetime import datetime
from typing import List, Optional
from ..db.database import get_db
from ..db.models import NotificationCreate
from .connection_manager import manager

logger = logging.getLogger("notification_server.service")

class NotificationService:
    @staticmethod
    async def create_notification(notif: NotificationCreate) -> dict:
        """Create and persist notification, then attempt immediate real-time dispatch."""
        notif_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        payload_json = json.dumps(notif.data or {})
        
        # 1. Save in database with status 'pending'
        async with get_db() as db:
            await db.execute("""
                INSERT INTO notifications (
                    id, source, title, message, priority, 
                    category, target_device, payload_data, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending');
            """, (
                notif_id, notif.source, notif.title, notif.message,
                notif.priority, notif.category, notif.target_device or 'all',
                payload_json, created_at
            ))
            await db.commit()
            
        record = {
            "id": notif_id,
            "source": notif.source,
            "title": notif.title,
            "message": notif.message,
            "priority": notif.priority,
            "category": notif.category,
            "target_device": notif.target_device or 'all',
            "data": notif.data or {},
            "created_at": created_at,
            "status": "pending"
        }
        
        # 2. Dispatch real-time WebSocket packet
        ws_packet = {
            "type": "notification",
            "notification": record
        }
        
        delivered = False
        if notif.target_device and notif.target_device != "all":
            # Targeted device
            delivered = await manager.send_to_device(notif.target_device, ws_packet)
        else:
            # Broadcast to all connected
            delivered_count = await manager.broadcast(ws_packet)
            delivered = delivered_count > 0
            
        # 3. If delivered immediately, update status
        if delivered:
            delivered_at = datetime.utcnow().isoformat()
            async with get_db() as db:
                await db.execute("""
                    UPDATE notifications 
                    SET status = 'delivered', delivered_at = ? 
                    WHERE id = ?;
                """, (delivered_at, notif_id))
                await db.commit()
            record["status"] = "delivered"
            record["delivered_at"] = delivered_at
            
        # 4. Notify live web dashboards
        await manager.broadcast_to_dashboards({
            "type": "new_notification",
            "notification": record
        })
        
        return record

    @staticmethod
    async def get_pending_for_device(device_id: str, limit: int = 50) -> List[dict]:
        """Fetch pending / unacknowledged notifications for a reconnecting device."""
        async with get_db() as db:
            cursor = await db.execute("""
                SELECT id, source, title, message, priority, category, target_device, payload_data, created_at, status
                FROM notifications
                WHERE (target_device = ? OR target_device = 'all')
                  AND status != 'acknowledged'
                ORDER BY created_at ASC
                LIMIT ?;
            """, (device_id, limit))
            rows = await cursor.fetchall()
            
            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "source": r["source"],
                    "title": r["title"],
                    "message": r["message"],
                    "priority": r["priority"],
                    "category": r["category"],
                    "target_device": r["target_device"],
                    "data": json.loads(r["payload_data"] or "{}"),
                    "created_at": r["created_at"],
                    "status": r["status"]
                })
            return results

    @staticmethod
    async def acknowledge_notifications(notification_ids: List[str], device_id: str):
        """Mark notifications as acknowledged by the client."""
        if not notification_ids:
            return
            
        now = datetime.utcnow().isoformat()
        placeholders = ",".join(["?"] * len(notification_ids))
        async with get_db() as db:
            await db.execute(f"""
                UPDATE notifications
                SET status = 'acknowledged', acknowledged_at = ?
                WHERE id IN ({placeholders});
            """, [now] + notification_ids)
            await db.commit()
            
        logger.info(f"Device {device_id} acknowledged {len(notification_ids)} notification(s)")

notification_service = NotificationService()
