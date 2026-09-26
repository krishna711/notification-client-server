import asyncio
import json
import os
import sys
import logging
import threading
import time
import uvicorn

# Add server and sdk paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk", "python")))

from app.core.config import settings
from app.db.database import init_db, get_db
from notifier_sdk import Notifier
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e_test")

def start_server_in_thread(server):
    server.run()

async def run_tests():
    print("=" * 60)
    print("RUNNING END-TO-END NOTIFICATION SYSTEM VERIFICATION")
    print("=" * 60)
    
    # Clean previous test database if any
    if os.path.exists("test_notifications.db"):
        try: os.remove("test_notifications.db")
        except: pass
    settings.DATABASE_PATH = "test_notifications.db"

    # 1. Initialize SQLite Database
    await init_db()
    print("[OK] SQLite Database Initialized")

    # 2. Run uvicorn in dedicated background thread
    from app.main import app
    config = uvicorn.Config(app, host="127.0.0.1", port=8005, log_level="warning")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=start_server_in_thread, args=(server,), daemon=True)
    server_thread.start()
    
    # Wait for server thread to start listening
    await asyncio.sleep(1.5)
    print("[OK] Test Server Running on http://127.0.0.1:8005")

    # 3. Test Client Connection & Handshake
    device_id = "test-laptop-1"
    token = settings.DEVICE_AUTH_TOKEN
    ws_url = f"ws://127.0.0.1:8005/ws/connect?token={token}&device_id={device_id}&device_name=Test+Laptop"
    
    async with websockets.connect(ws_url) as ws:
        # Expect connection established
        handshake_msg = json.loads(await ws.recv())
        assert handshake_msg["type"] == "connection_established", f"Unexpected handshake: {handshake_msg}"
        print(f"[OK] WebSocket Handshake Verified for {device_id}")

        # 4. Fire Real-time Notification from SDK
        sdk = Notifier(endpoint="http://127.0.0.1:8005", api_key="dev-secret-api-key", default_source="app1-algo")
        res = await asyncio.to_thread(
            sdk.trade_alert,
            title="NIFTY Order Executed",
            message="25000 CE filled @ 142.50",
            priority="high",
            data={"order_id": "ORD-1234"}
        )
        notif_id = res["notification_id"]
        print(f"[OK] Producer SDK Ingested Alert (ID: {notif_id})")

        # 5. Receive Live Push on Client
        received_raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
        received_pkt = json.loads(received_raw)
        assert received_pkt["type"] == "notification"
        assert received_pkt["notification"]["id"] == notif_id
        assert received_pkt["notification"]["title"] == "NIFTY Order Executed"
        print(f"[OK] Real-time Push Received by Client (Title: '{received_pkt['notification']['title']}')")

        # 6. Send ACK from Client
        await ws.send(json.dumps({"type": "ack", "notification_ids": [notif_id]}))
        await asyncio.sleep(0.4)
        
        # Verify status in database is 'acknowledged'
        async with get_db() as db:
            cursor = await db.execute("SELECT status FROM notifications WHERE id = ?", (notif_id,))
            row = await cursor.fetchone()
            assert row["status"] == "acknowledged"
            print("[OK] Notification ACK Verified: Status updated to 'acknowledged' in DB")

    print("\n[OK] Live Real-Time Push & ACK Workflow Passed Successfully!")

    # 7. Test Offline Queuing & Catch-up
    print("\nTesting Offline Buffer & Reconnection Catch-up...")
    # Client is now disconnected!
    # Send 2 notifications while client is offline:
    offline_alert_1 = await asyncio.to_thread(sdk.send, "Offline Alert 1", "Generated while laptop was asleep", priority="normal")
    offline_alert_2 = await asyncio.to_thread(sdk.send, "Offline Alert 2", "Critical server alert during disconnect", priority="critical")
    print(f"[OK] Sent 2 alerts while client was offline: {offline_alert_1['notification_id']}, {offline_alert_2['notification_id']}")

    # Reconnect client
    async with websockets.connect(ws_url) as ws_reconnect:
        hs = json.loads(await ws_reconnect.recv())
        assert hs["type"] == "connection_established"
        
        # Expect the 2 queued notifications to arrive immediately
        rec_1 = json.loads(await asyncio.wait_for(ws_reconnect.recv(), timeout=3.0))
        rec_2 = json.loads(await asyncio.wait_for(ws_reconnect.recv(), timeout=3.0))
        
        delivered_ids = [rec_1["notification"]["id"], rec_2["notification"]["id"]]
        assert offline_alert_1["notification_id"] in delivered_ids
        assert offline_alert_2["notification_id"] in delivered_ids
        assert rec_1.get("offline_buffer") is True
        print(f"[OK] Offline Buffer Catch-up Verified: Received both missed notifications upon reconnect!")

        # ACK both
        await ws_reconnect.send(json.dumps({"type": "ack", "notification_ids": delivered_ids}))
        await asyncio.sleep(0.4)

    # Clean shutdown
    server.should_exit = True
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! FULL SYSTEM END-TO-END CERTIFIED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
