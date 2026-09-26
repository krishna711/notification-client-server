import os
from typing import List

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Central Notification Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server bind
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security: API keys for external producer apps (App1, App2, App3)
    # Comma-separated list in env var NOTIFICATION_API_KEYS
    API_KEYS: str = os.getenv("NOTIFICATION_API_KEYS", "dev-secret-api-key,app1-trading-key,app2-monitor-key")
    
    # Security: Shared or per-device secret token for client WebSocket authentication
    DEVICE_AUTH_TOKEN: str = os.getenv("DEVICE_AUTH_TOKEN", "dev-device-secret-token")
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "notifications.db")
    
    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = 25  # seconds
    WS_HEARTBEAT_TIMEOUT: int = 60   # seconds
    
    # Offline notification retention (days)
    OFFLINE_RETENTION_DAYS: int = 7
    
    @property
    def valid_api_keys(self) -> List[str]:
        return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
