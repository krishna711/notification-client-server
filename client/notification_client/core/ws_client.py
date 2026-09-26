import asyncio
import json
import logging
from typing import Callable, Optional, List
import websockets
from ..config import config
from .notifier import notifier

logger = logging.getLogger("notification_client.ws")

class NotificationWebSocketClient:
    def __init__(self, on_status_change: Optional[Callable[[str], None]] = None):
        self.on_status_change = on_status_change
        self.running = False
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.recent_notifications: List[dict] = []
        self.status = "disconnected"  # connected, connecting, disconnected
        self.paused = False

    def _set_status(self, new_status: str):
        self.status = new_status
        logger.info(f"Client status changed to: {new_status}")
        if self.on_status_change:
            self.on_status_change(new_status)

    async def start(self):
        """Main lifecycle loop with exponential backoff auto-reconnect."""
        self.running = True
        self.loop = asyncio.get_running_loop()
        delay = config.MIN_RECONNECT_DELAY

        logger.info(f"Starting Notification Client for device: {config.DEVICE_ID}")
        
        while self.running:
            try:
                self._set_status("connecting")
                target_url = config.ws_url
                logger.info(f"Connecting to Gateway: {config.SERVER_URL}...")
                
                async with websockets.connect(
                    target_url,
                    ping_interval=None  # We handle our own heartbeat
                ) as ws:
                    self.ws = ws
                    self._set_status("connected")
                    delay = config.MIN_RECONNECT_DELAY  # Reset backoff on success
                    
                    # Launch background ping worker
                    heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))
                    
                    # Listen loop
                    try:
                        async for raw_msg in ws:
                            await self._handle_message(raw_msg, ws)
                    finally:
                        heartbeat_task.cancel()
                        
            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                self._set_status("disconnected")
                if not self.running:
                    break
                logger.warning(f"Connection lost ({e}). Reconnecting in {delay:.1f}s...")
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, config.MAX_RECONNECT_DELAY)
            except Exception as e:
                self._set_status("disconnected")
                if not self.running:
                    break
                logger.error(f"Unexpected connection error: {e}. Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, config.MAX_RECONNECT_DELAY)

    async def _heartbeat_loop(self, ws):
        """Sends periodic ping to maintain persistent connection through firewalls/proxies."""
        while self.running:
            try:
                await asyncio.sleep(config.HEARTBEAT_INTERVAL)
                await ws.send(json.dumps({"type": "ping"}))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Heartbeat send failed: {e}")
                break

    async def _handle_message(self, raw_msg: str, ws):
        """Parse incoming messages from Notification Gateway."""
        try:
            data = json.loads(raw_msg)
            msg_type = data.get("type")

            if msg_type == "connection_established":
                logger.info(f"Gateway Handshake Accepted: {data.get('message')}")

            elif msg_type == "notification":
                notif = data.get("notification", {})
                notif_id = notif.get("id")
                is_offline = data.get("offline_buffer", False)
                
                # Store in recent history
                self.recent_notifications.insert(0, notif)
                if len(self.recent_notifications) > 50:
                    self.recent_notifications.pop()
                    
                # Display Windows Toast (unless paused)
                if not self.paused:
                    title = notif.get("title", "New Notification")
                    if is_offline:
                        title = f"[Caught Up] {title}"
                    notifier.notify(
                        title=title,
                        message=notif.get("message", ""),
                        priority=notif.get("priority", "normal"),
                        source=notif.get("source", "system"),
                        data=notif.get("data")
                    )

                # Send ACK back to server immediately
                if notif_id:
                    await ws.send(json.dumps({
                        "type": "ack",
                        "notification_ids": [notif_id]
                    }))
                    logger.debug(f"Acknowledged notification: {notif_id}")

            elif msg_type == "pong":
                logger.debug("Received Gateway heartbeat pong")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def trigger_reconnect(self):
        """Forces WebSocket client to immediately reconnect using updated config."""
        logger.info("Reconnection requested with updated settings...")
        if self.ws and hasattr(self, "loop") and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
            except Exception as e:
                logger.debug(f"Error triggering socket close: {e}")

    def stop(self):
        """Stop client and close connections."""
        self.running = False
        if self.ws and hasattr(self, "loop") and self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
            except Exception:
                pass
        self._set_status("disconnected")
