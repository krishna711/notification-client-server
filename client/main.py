import asyncio
import logging
import threading
import sys
import os

# Add client folder to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notification_client.config import config
from notification_client.core.ws_client import NotificationWebSocketClient
from notification_client.ui.tray import NotificationTrayApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("notification_client")

def run_ws_loop(ws_client):
    """Run asyncio event loop in a dedicated background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ws_client.start())
    except Exception as e:
        logger.error(f"WebSocket thread stopped: {e}")
    finally:
        loop.close()

def main():
    print("=" * 60)
    print(" 🔔 Notification Gateway - Windows Client")
    print(f" Target Gateway: {config.SERVER_URL}")
    print(f" Device ID:      {config.DEVICE_ID}")
    print("=" * 60)

    # 1. Initialize Tray App and WS Client
    tray_app = None
    
    def on_status_change(status: str):
        if tray_app:
            tray_app.update_status(status)

    ws_client = NotificationWebSocketClient(on_status_change=on_status_change)
    tray_app = NotificationTrayApp(ws_client)

    # 2. Launch WebSocket listener in background thread
    ws_thread = threading.Thread(target=run_ws_loop, args=(ws_client,), daemon=True)
    ws_thread.start()

    # 3. Run System Tray message loop on main thread
    try:
        tray_app.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping client...")
        ws_client.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
