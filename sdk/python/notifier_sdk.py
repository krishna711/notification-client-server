import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

class Notifier:
    """
    Lightweight, zero-dependency Python SDK for external applications (App 1, App 2, App 3)
    to dispatch notifications to your central Notification Gateway.
    """
    def __init__(
        self,
        endpoint: str = "http://localhost:8000",
        api_key: str = "dev-secret-api-key",
        default_source: str = "app"
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.default_source = default_source
        self.notify_url = f"{self.endpoint}/api/v1/notify"

    def send(
        self,
        title: str,
        message: str,
        priority: str = "normal",
        category: str = "general",
        target_device: str = "all",
        source: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0
    ) -> dict:
        """
        Send a notification to the central gateway.
        
        :param title: Header text for notification popup
        :param message: Main message content
        :param priority: 'low', 'normal', 'high', 'critical'
        :param category: Optional classification (e.g. 'trade', 'server_health')
        :param target_device: Specific device_id or 'all' for broadcast
        :param source: Override sending app name
        :param data: Arbitrary custom JSON-serializable dictionary
        :param timeout: Request timeout in seconds
        :return: Gateway response dict
        """
        payload = {
            "source": source or self.default_source,
            "title": title,
            "message": message,
            "priority": priority,
            "category": category,
            "target_device": target_device,
            "data": data or {}
        }
        
        req_data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": f"NotifierSDK/1.0.0 ({source or self.default_source})"
        }
        
        req = urllib.request.Request(self.notify_url, data=req_data, headers=headers, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_bytes = response.read()
                return json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"Notification Gateway returned HTTP {e.code}: {err_msg}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to connect to Notification Gateway at {self.notify_url}: {e.reason}")

    # Convenience shortcuts
    def trade_alert(self, title: str, message: str, priority: str = "high", data: Optional[Dict[str, Any]] = None) -> dict:
        return self.send(title, message, priority=priority, category="trade", data=data)

    def server_alert(self, title: str, message: str, priority: str = "critical", data: Optional[Dict[str, Any]] = None) -> dict:
        return self.send(title, message, priority=priority, category="server_health", data=data)

    def info(self, title: str, message: str, data: Optional[Dict[str, Any]] = None) -> dict:
        return self.send(title, message, priority="normal", category="info", data=data)
