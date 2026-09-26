import os
import sys
import json
import platform
import re
import urllib.parse
from typing import Dict, Any

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

class ClientConfig:
    def __init__(self):
        # Default device naming
        raw_node = platform.node().lower()
        clean_node = re.sub(r'[^a-zA-Z0-9_-]', '-', raw_node)
        
        self._default_device_id = f"{clean_node}-laptop"
        self._default_device_name = f"{platform.node()} (Windows)"
        
        # In-memory settings
        self.server_url: str = "http://localhost:8000"
        self.device_id: str = self._default_device_id
        self.device_name: str = self._default_device_name
        self.device_token: str = "dev-device-secret-token"
        
        # Notification settings: 'center', 'toast', or 'both'
        self.notification_style: str = "center"
        self.enable_sound: bool = True
        self.duration_seconds: int = 7
        
        # Connection timeouts
        self.min_reconnect_delay: float = 1.0
        self.max_reconnect_delay: float = 30.0
        self.heartbeat_interval: float = 20.0
        
        # Load from config.json or environment
        self.load()

    @property
    def SERVER_URL(self) -> str:
        return self.server_url

    @property
    def DEVICE_ID(self) -> str:
        return self.device_id

    @property
    def DEVICE_NAME(self) -> str:
        return self.device_name

    @property
    def DEVICE_TOKEN(self) -> str:
        return self.device_token

    @property
    def NOTIFICATION_STYLE(self) -> str:
        return self.notification_style

    @property
    def ENABLE_SOUND(self) -> bool:
        return self.enable_sound

    @property
    def TOAST_DURATION(self) -> int:
        return self.duration_seconds

    @property
    def MIN_RECONNECT_DELAY(self) -> float:
        return self.min_reconnect_delay

    @property
    def MAX_RECONNECT_DELAY(self) -> float:
        return self.max_reconnect_delay

    @property
    def HEARTBEAT_INTERVAL(self) -> float:
        return self.heartbeat_interval

    @property
    def ws_url(self) -> str:
        base = self.server_url.strip()
        if base.startswith("https://"):
            ws_base = "wss://" + base[8:]
        elif base.startswith("http://"):
            ws_base = "ws://" + base[7:]
        elif base.startswith("wss://") or base.startswith("ws://"):
            ws_base = base
        else:
            ws_base = f"ws://{base}"
            
        ws_base = ws_base.rstrip("/")
        
        query_params = {
            "token": self.device_token,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "version": "1.1.0"
        }
        encoded_query = urllib.parse.urlencode(query_params)
        return f"{ws_base}/ws/connect?{encoded_query}"

    def load(self):
        """Load configuration from config.json if it exists, otherwise use env or defaults."""
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.server_url = data.get("server_url", self.server_url)
                    self.device_id = data.get("device_id", self.device_id)
                    self.device_name = data.get("device_name", self.device_name)
                    self.device_token = data.get("device_token", self.device_token)
                    self.notification_style = data.get("notification_style", self.notification_style)
                    self.enable_sound = data.get("enable_sound", self.enable_sound)
                    self.duration_seconds = int(data.get("duration_seconds", self.duration_seconds))
                    return
            except Exception as e:
                print(f"[Config] Error loading config.json: {e}")

        # Fallback to environment variables
        self.server_url = os.getenv("NOTIFIER_SERVER_URL", self.server_url)
        self.device_id = os.getenv("NOTIFIER_DEVICE_ID", self.device_id)
        self.device_name = os.getenv("NOTIFIER_DEVICE_NAME", self.device_name)
        self.device_token = os.getenv("NOTIFIER_DEVICE_TOKEN", self.device_token)
        self.notification_style = os.getenv("NOTIFIER_STYLE", self.notification_style)
        self.enable_sound = os.getenv("NOTIFIER_SOUND", "true").lower() in ("true", "1", "yes")
        
        # Save initial file for user convenience
        self.save()

    def save(self):
        """Save current configuration to config.json."""
        data = {
            "server_url": self.server_url,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_token": self.device_token,
            "notification_style": self.notification_style,
            "enable_sound": self.enable_sound,
            "duration_seconds": self.duration_seconds
        }
        try:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Config] Error saving config.json: {e}")

    def update(self, **kwargs):
        """Update settings and persist to disk."""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.save()

config = ClientConfig()
