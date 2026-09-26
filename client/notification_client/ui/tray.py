import logging
import threading
from typing import Optional
from PIL import Image, ImageDraw
from ..config import config
from ..core.notifier import notifier
from .settings_dialog import SettingsDialog

logger = logging.getLogger("notification_client.tray")

def create_status_image(color: str) -> Image.Image:
    """Generate dynamic 64x64 status icon for Windows system tray."""
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Outer circle / badge
    draw.ellipse((4, 4, 60, 60), fill="#1e293b", outline="#334155", width=2)
    
    # Inner status dot
    colors = {
        "green": "#10b981",
        "amber": "#f59e0b",
        "red": "#ef4444"
    }
    fill_color = colors.get(color, "#94a3b8")
    draw.ellipse((16, 16, 48, 48), fill=fill_color)
    return image

class NotificationTrayApp:
    def __init__(self, ws_client):
        self.ws_client = ws_client
        self.icon = None
        self._has_pystray = False
        
        try:
            import pystray
            self._has_pystray = True
        except ImportError:
            self._has_pystray = False
            logger.warning("pystray not installed. Running in console mode without system tray icon.")

    def run(self):
        """Run system tray icon loop."""
        if not self._has_pystray:
            logger.info("Tray loop running in console mode. Press Ctrl+C to exit.")
            return

        import pystray
        
        self.icon = pystray.Icon(
            "notification_gateway_client",
            create_status_image("amber"),
            title=f"Notification Client: Connecting ({config.DEVICE_ID})",
            menu=self._create_menu()
        )
        self.icon.run()

    def update_status(self, status: str):
        """Update tray icon image and title based on connection status."""
        if not self.icon or not self._has_pystray:
            return

        status_map = {
            "connected": ("green", f"🟢 Connected ({config.DEVICE_ID})"),
            "connecting": ("amber", f"🟡 Connecting ({config.DEVICE_ID})"),
            "disconnected": ("red", f"🔴 Disconnected ({config.DEVICE_ID})")
        }
        color, title = status_map.get(status, ("red", f"Notification Client ({config.DEVICE_ID})"))
        
        self.icon.icon = create_status_image(color)
        self.icon.title = title
        # Refresh menu to update pause state / device info
        self.icon.menu = self._create_menu()

    def _create_menu(self):
        import pystray
        
        paused_label = "▶ Resume Notifications" if self.ws_client.paused else "⏸ Pause Notifications"
        curr_style = config.notification_style
        
        def set_style(style_name):
            def handler():
                config.update(notification_style=style_name)
                logger.info(f"Notification display style changed to: {style_name}")
                if self.icon:
                    self.icon.menu = self._create_menu()
                notifier.notify(
                    title="Display Style Updated",
                    message=f"Active mode: {style_name.upper()} (Saved to config.json)",
                    priority="normal",
                    source="settings"
                )
            return handler

        style_center_label = ("✓ " if curr_style == "center" else "   ") + "🎯 Center Screen Banner"
        style_toast_label  = ("✓ " if curr_style == "toast"  else "   ") + "🪟 Windows Toast (Bottom-Right)"
        style_both_label   = ("✓ " if curr_style == "both"   else "   ") + "🔀 Both (Center & Toast)"

        # Truncate server URL if long for clean display
        disp_url = config.server_url
        if len(disp_url) > 32:
            disp_url = disp_url[:30] + "..."

        return pystray.Menu(
            pystray.MenuItem(f"Status: {self.ws_client.status.upper()}", lambda: None, enabled=False),
            pystray.MenuItem(f"Gateway: {disp_url}", lambda: None, enabled=False),
            pystray.MenuItem(f"Device: {config.device_id}", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙ Settings...", self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Notification Style:", lambda: None, enabled=False),
            pystray.MenuItem(style_center_label, set_style("center")),
            pystray.MenuItem(style_toast_label, set_style("toast")),
            pystray.MenuItem(style_both_label, set_style("both")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(paused_label, self._toggle_pause),
            pystray.MenuItem("🔔 Send Test Notification", self._send_test_alert),
            pystray.MenuItem(f"📜 Recent Alerts ({len(self.ws_client.recent_notifications)})", self._show_recent),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Exit", self._on_exit)
        )

    def _open_settings(self):
        """Open settings dialog and handle reconnect if server URL/credentials change."""
        def on_saved():
            logger.info("Settings saved. Triggering client reconnection...")
            if self.icon:
                self.icon.menu = self._create_menu()
            self.ws_client.trigger_reconnect()
            notifier.notify(
                title="Settings Applied",
                message=f"Connecting to: {config.server_url}",
                priority="normal",
                source="settings"
            )

        SettingsDialog.open(on_save_callback=on_saved)

    def _toggle_pause(self):
        self.ws_client.paused = not self.ws_client.paused
        state = "paused" if self.ws_client.paused else "resumed"
        logger.info(f"Notifications {state}")
        if self.icon:
            self.icon.menu = self._create_menu()
        notifier.notify(
            title="Notification Gateway",
            message=f"Alerts are now {state}.",
            priority="low",
            source="client"
        )

    def _send_test_alert(self):
        notifier.notify(
            title="Local Test Alert",
            message=f"Display style '{config.notification_style.upper()}' is working properly!",
            priority="high",
            source="client",
            data={"style": config.notification_style, "server": config.server_url}
        )

    def _show_recent(self):
        if not self.ws_client.recent_notifications:
            notifier.notify("Notification History", "No notifications received yet.", "low", "client")
            return
            
        recent = self.ws_client.recent_notifications[:3]
        summary = "\n".join([f"• [{r.get('source', '')}] {r.get('title', '')}" for r in recent])
        notifier.notify(
            title="Recent Notifications",
            message=summary,
            priority="normal",
            source="client"
        )

    def _on_exit(self):
        logger.info("Exiting Notification Client...")
        self.ws_client.stop()
        if self.icon:
            self.icon.stop()
