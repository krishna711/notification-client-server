# 🔔 Central Notification Gateway & Windows Client

A high-performance, real-time notification infrastructure allowing multiple independent applications (`app1`, `app2`, `app3` across multiple Linux/cloud servers) to push instant desktop notifications and audio alerts to your Windows laptop **without opening inbound router ports or configuring fragile port-forwarding**.

---

## 🏛️ Architecture

```text
  [ Linux App 1 ] ──┐
  [ Linux App 2 ] ──┼──( HTTPS POST /api/v1/notify )──▶ [ Cloudflare Tunnel ]
  [ Remote App 3 ] ─┘                                            │
                                                                 ▼
                                                  ┌─────────────────────────────┐
                                                  │ Central Notification Server │
                                                  │ FastAPI + SQLite WAL Mode   │
                                                  │ Device Registry & Queuing   │
                                                  └──────────────┬──────────────┘
                                                                 │
                                                    Persistent Outbound WSS
                                                   (wss://notify.domain.com/ws)
                                                                 │
                                                                 ▼
                                                  ┌─────────────────────────────┐
                                                  │    Windows Desktop Client   │
                                                  │  System Tray (🟢/🟡/🔴)    │
                                                  │  Action Center Native Toast │
                                                  │  Audio Alert (Chimes/Beep)  │
                                                  │  Auto-reconnect with Backoff│
                                                  └─────────────────────────────┘
```

### Why this architecture is rock-solid:
1. **Outbound-only connection from your laptop**: Your laptop connects *outbound* to the gateway via WebSocket. This bypasses home/office firewalls, NAT, and CGNAT effortlessly.
2. **At-Least-Once Delivery**: If your laptop is asleep, closed-lid, or disconnected, the gateway holds notifications in an offline SQLite queue. The instant your laptop reconnects, all missed notifications are delivered and acknowledged.
3. **Multi-App Decoupling**: External applications simply send a standard `HTTPS POST` with an API key. They never need to know your laptop's IP or connection state.
4. **Permanent Domain via Cloudflare Tunnel**: Runs 24/7 without changing URLs, dynamic DNS headaches, or opening any ports on your router.

---

## 🚀 Quick Start (Local Testing)

### 1. Install Dependencies
```bash
# In the repository root
python -m pip install -r server/requirements.txt
python -m pip install -r client/requirements.txt
```

### 2. Start the Gateway Server
```bash
python server/run_server.py
```
- Gateway URL: `http://localhost:8000`
- Web Console: Open `http://localhost:8000` in your browser to view the live dashboard and connected devices.

### 3. Launch the Windows Client
In a separate terminal:
```bash
python client/main.py
```
- You will see the Notification Gateway icon appear in your **Windows System Tray**.
- It shows 🟢 **Connected** and announces itself to the gateway.
- Check `http://localhost:8000` — your Windows device will now show as **ONLINE**!

---

## 🎨 Dual Notification Display Modes (Switchable)

You can toggle how notifications are rendered on your laptop:

1. **🎯 Center Screen Banner (Focused Overlay)**:
   - High-visibility popup that appears right in the **dead center of your laptop screen**.
   - Frameless dark theme with color-coded priority glow (Red for `Critical`, Amber for `High`, Blue for `Normal`).
   - Shows source app, title, message body, and custom data payload.
   - Dismiss with a single click or press `Esc` / `Space` / `Enter`. Includes automatic countdown timer.
2. **🪟 Windows Toast (Bottom-Right Corner)**:
   - Modern Windows Action Center notification banner in the bottom-right corner.
   - Persists in Windows Notification Center history.
3. **🔀 Both (Center Banner + Windows Toast)**:
   - Displays both simultaneously: maximum screen focus plus Windows history logging!

> **How to Switch**: Right-click the system tray icon and click `🎯 Center Screen Banner`, `🪟 Windows Toast`, or `🔀 Both`. The setting saves instantly to `client/config.json`.

---

## ⚙️ Switching Between Local & Production (No Rebuilding)

You can switch your client from your local server (`http://localhost:8000`) to your live production server (`https://notify.yourdomain.com`) in 2 simple ways without rebuilding or reinstalling:

### Option A: From the System Tray (GUI)
1. Right-click the tray icon and click **⚙ Settings...**
2. Change the **Gateway Server URL** to your live production URL (e.g. `https://notify.yourdomain.com`)
3. Update the **Device Auth Token** (if different)
4. Click **💾 Save & Reconnect**
5. The client drops the local socket and immediately connects to production live!

### Option B: Via `client/config.json`
Simply edit `client/config.json`:
```json
{
  "server_url": "https://notify.yourdomain.com",
  "device_id": "laptop-asus-laptop",
  "device_name": "LAPTOP-ASUS (Windows)",
  "device_token": "your-production-device-token",
  "notification_style": "center",
  "enable_sound": true,
  "duration_seconds": 7
}
```

---
You can send notifications from:
1. The **Web Dashboard** at `http://localhost:8000` (click "Dispatch Alert")
2. The provided test scripts:
```bash
python sdk/examples/app1_trading.py
python sdk/examples/app2_monitor.py
python sdk/examples/simulate_multi_apps.py
```
3. Or raw `curl`:
```bash
curl -X POST "http://localhost:8000/api/v1/notify" \
  -H "Authorization: Bearer dev-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "trading-strategy-17",
    "title": "Target Hit",
    "message": "NIFTY 25000 CE target reached @ 165.00 (+40 pts)",
    "priority": "high",
    "target_device": "all"
  }'
```

---

## 📦 Using the Python Producer SDK in your Apps

Drop `sdk/python/notifier_sdk.py` into any of your projects:

```python
from notifier_sdk import Notifier

# Initialize with your gateway URL & API key
notify = Notifier(
    endpoint="https://notify.yourdomain.com",
    api_key="your-secret-api-key",
    default_source="my-trading-app"
)

# Standard notification
notify.send(
    title="Order Executed",
    message="Buy 50 shares of TCS @ 3850",
    priority="high"  # 'low', 'normal', 'high', 'critical'
)

# Convenience shortcuts
notify.trade_alert("Target Hit", "SL moved to breakeven", priority="high")
notify.server_alert("Database Backup Failed", "Disk write error", priority="critical")
```

---

## 🌐 Production Deployment with Cloudflare Tunnel

### Step 1: Deploy Gateway on your Linux Server
You can run it with Docker Compose:
```bash
cd deployment
docker compose up -d
```
Or directly as a systemd service using `deployment/systemd/notification-gateway.service`.

### Step 2: Configure Cloudflare Tunnel
1. Install `cloudflared` on the Linux server:
   ```bash
   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared.deb
   ```
2. Login and create your tunnel:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create notification-gateway
   cloudflared tunnel route dns notification-gateway notify.yourdomain.com
   ```
3. Configure `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <YOUR-TUNNEL-ID>
   credentials-file: /root/.cloudflared/<YOUR-TUNNEL-ID>.json

   ingress:
     - hostname: notify.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```
4. Start tunnel as a service:
   ```bash
   sudo cloudflared service install
   sudo systemctl start cloudflared
   ```

### Step 3: Point Windows Client to Cloudflare URL
In your Windows client environment variables or `client/notification_client/config.py`:
```python
SERVER_URL = "https://notify.yourdomain.com"
DEVICE_TOKEN = "your-production-device-secret-token"
```

---

## 🪟 Packaging Windows Client to .EXE & Auto-Start
To bundle the client into a single `.exe` that launches silently at Windows startup:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile client/main.py -n "NotificationClient"
```
Place a shortcut to `NotificationClient.exe` in your Windows Startup folder:
`shell:startup` (Press `Win + R`, type `shell:startup`, and paste the shortcut).
