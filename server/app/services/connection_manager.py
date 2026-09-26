import logging
import asyncio
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from datetime import datetime
from ..db.database import get_db

logger = logging.getLogger("notification_server.connections")

class ConnectionManager:
    def __init__(self):
        # device_id -> set of active WebSockets (allows same device to have multiple connections if needed)
        self.device_connections: Dict[str, Set[WebSocket]] = {}
        # Dashboard listeners for live monitoring web UI
        self.dashboard_listeners: Set[WebSocket] = set()
        # Track device metadata
        self.device_metadata: Dict[str, Dict[str, Any]] = {}

    async def register_device(
        self, 
        device_id: str, 
        device_name: str, 
        websocket: WebSocket, 
        ip_address: str = "", 
        client_version: str = "1.0.0"
    ):
        """Accept WebSocket and record device as online."""
        await websocket.accept()
        if device_id not in self.device_connections:
            self.device_connections[device_id] = set()
        self.device_connections[device_id].add(websocket)
        
        self.device_metadata[device_id] = {
            "device_name": device_name,
            "ip_address": ip_address,
            "client_version": client_version,
            "connected_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat()
        }
        
        # Persist online status to SQLite
        try:
            async with get_db() as db:
                await db.execute("""
                    INSERT INTO devices (device_id, device_name, last_seen, is_online, ip_address, client_version)
                    VALUES (?, ?, CURRENT_TIMESTAMP, 1, ?, ?)
                    ON CONFLICT(device_id) DO UPDATE SET
                        device_name = excluded.device_name,
                        last_seen = CURRENT_TIMESTAMP,
                        is_online = 1,
                        ip_address = excluded.ip_address,
                        client_version = excluded.client_version;
                """, (device_id, device_name, ip_address, client_version))
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update device online state in DB: {e}")

        logger.info(f"Device connected: {device_id} ({device_name}) from {ip_address}")
        await self.broadcast_to_dashboards({
            "type": "device_status",
            "device_id": device_id,
            "device_name": device_name,
            "status": "online"
        })

    async def disconnect_device(self, device_id: str, websocket: WebSocket):
        """Remove WebSocket connection and mark offline if no connections remain."""
        if device_id in self.device_connections:
            self.device_connections[device_id].discard(websocket)
            if not self.device_connections[device_id]:
                del self.device_connections[device_id]
                # Update DB offline status
                try:
                    async with get_db() as db:
                        await db.execute("""
                            UPDATE devices 
                            SET is_online = 0, last_seen = CURRENT_TIMESTAMP 
                            WHERE device_id = ?;
                        """, (device_id,))
                        await db.commit()
                except Exception as e:
                    logger.error(f"Failed to update device offline state in DB: {e}")
                    
                logger.info(f"Device disconnected: {device_id}")
                await self.broadcast_to_dashboards({
                    "type": "device_status",
                    "device_id": device_id,
                    "status": "offline"
                })

    def is_device_online(self, device_id: str) -> bool:
        return device_id in self.device_connections and len(self.device_connections[device_id]) > 0

    def get_online_devices(self) -> Dict[str, Dict[str, Any]]:
        return {dev_id: self.device_metadata.get(dev_id, {}) for dev_id in self.device_connections}

    async def send_to_device(self, device_id: str, message: dict) -> bool:
        """Send message to a specific device. Returns True if delivered to at least one socket."""
        sockets = self.device_connections.get(device_id)
        if not sockets:
            return False
            
        delivered = False
        dead_sockets = set()
        for ws in list(sockets):
            try:
                await ws.send_json(message)
                delivered = True
            except Exception as e:
                logger.warning(f"Failed to send to socket of {device_id}: {e}")
                dead_sockets.add(ws)
                
        for dead_ws in dead_sockets:
            sockets.discard(dead_ws)
            
        return delivered

    async def broadcast(self, message: dict) -> int:
        """Broadcast message to all connected devices. Returns number of devices delivered to."""
        count = 0
        for dev_id in list(self.device_connections.keys()):
            if await self.send_to_device(dev_id, message):
                count += 1
        return count

    # Dashboard real-time monitoring support
    async def register_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_listeners.add(websocket)

    async def disconnect_dashboard(self, websocket: WebSocket):
        self.dashboard_listeners.discard(websocket)

    async def broadcast_to_dashboards(self, event: dict):
        dead = set()
        for ws in list(self.dashboard_listeners):
            try:
                await ws.send_json(event)
            except Exception:
                dead.add(ws)
        for d in dead:
            self.dashboard_listeners.discard(d)

manager = ConnectionManager()
