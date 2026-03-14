from typing import Any, Optional

from pydantic import BaseModel, Field


class InboundMessage(BaseModel):
    chat_id: str
    message_id: Optional[str] = None
    message_type: str = "unknown"
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_mime: Optional[str] = None
    media_base64: Optional[str] = None
    sender_name: Optional[str] = None
    timestamp: Optional[int] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
