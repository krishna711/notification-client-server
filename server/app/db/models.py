from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class NotificationCreate(BaseModel):
    source: str = Field(..., description="Name of sending app (e.g. app1, trading-bot)")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message body")
    priority: str = Field("normal", description="low, normal, high, critical")
    category: Optional[str] = Field("general", description="trade, alert, server, etc.")
    target_device: Optional[str] = Field("all", description="Specific device_id or 'all'")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arbitrary custom metadata")

class NotificationResponse(BaseModel):
    id: str
    source: str
    title: str
    message: str
    priority: str
    category: Optional[str]
    target_device: Optional[str]
    payload_data: Optional[str]
    created_at: str
    status: str
    delivered_at: Optional[str] = None
    acknowledged_at: Optional[str] = None

class NotificationAck(BaseModel):
    notification_ids: List[str] = Field(..., description="IDs to acknowledge receipt of")
    device_id: str

class DeviceStatus(BaseModel):
    device_id: str
    device_name: str
    last_seen: str
    is_online: bool
    ip_address: Optional[str] = None
    client_version: Optional[str] = None
