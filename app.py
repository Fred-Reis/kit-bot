"""app class, the main entrypoint to use FastAPI."""

from fastapi import FastAPI, Request
from sqlalchemy.exc import SQLAlchemyError

from config import AUTO_CREATE_DB, LOG_PAYLOADS
from db import Base, SessionLocal, engine
from logger import get_logger
from message_processor import process_inbound_media
from messages_buffer import buffer_message
from models import Event
from schemas import InboundMessage

app = FastAPI()
logger = get_logger("webhook")


@app.on_event("startup")
def startup():
    if AUTO_CREATE_DB:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created or verified.")
        except SQLAlchemyError as exc:
            logger.exception("Failed to create tables: %s", exc)

def extract_inbound_message(payload: dict) -> InboundMessage | None:
    data = payload.get("data") or {}
    key = data.get("key") or {}
    msg = data.get("message") or {}

    chat_id = key.get("remoteJid")
    if not chat_id:
        return None

    message_id = key.get("id")
    sender_name = data.get("pushName")
    timestamp = data.get("messageTimestamp")

    message_type = "unknown"
    text = None
    media_url = None
    media_mime = None
    media_base64 = None

    if isinstance(msg, dict):
        media_base64 = msg.get("base64")
        if "conversation" in msg:
            message_type = "text"
            text = msg.get("conversation")
        elif "extendedTextMessage" in msg:
            message_type = "text"
            text = (msg.get("extendedTextMessage") or {}).get("text")
        elif "imageMessage" in msg:
            message_type = "image"
            image = msg.get("imageMessage") or {}
            text = image.get("caption")
            media_mime = image.get("mimetype")
            media_url = image.get("url") or image.get("directPath")
        elif "documentMessage" in msg:
            message_type = "document"
            document = msg.get("documentMessage") or {}
            text = document.get("caption") or document.get("title")
            media_mime = document.get("mimetype")
            media_url = document.get("url") or document.get("directPath")

    return InboundMessage(
        chat_id=chat_id,
        message_id=message_id,
        message_type=message_type,
        text=text,
        media_url=media_url,
        media_mime=media_mime,
        media_base64=media_base64,
        sender_name=sender_name,
        timestamp=timestamp,
        raw_payload=payload,
    )


def redact_payload(payload: dict) -> dict:
    safe = dict(payload)
    data = safe.get("data")
    if isinstance(data, dict):
        message = data.get("message")
        if isinstance(message, dict) and "base64" in message:
            message = dict(message)
            base64_value = message.get("base64")
            if isinstance(base64_value, str):
                message["base64"] = f"<omitted:{len(base64_value)} chars>"
            else:
                message["base64"] = "<omitted>"
            data = dict(data)
            data["message"] = message
            safe["data"] = data
    return safe


def persist_inbound_event(inbound: InboundMessage) -> None:
    db = SessionLocal()
    try:
        event = Event(
            user_id=None,
            chat_id=inbound.chat_id,
            type="inbound.raw",
            payload_json={
                "message_id": inbound.message_id,
                "message_type": inbound.message_type,
                "text": inbound.text,
                "media_url": inbound.media_url,
                "media_mime": inbound.media_mime,
                "sender_name": inbound.sender_name,
                "timestamp": inbound.timestamp,
                "raw_payload": inbound.raw_payload,
            },
        )
        db.add(event)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to persist inbound event: %s", exc)
    finally:
        db.close()


@app.post("/webhook")
async def webhook(request: Request):
    """
    Handle incoming webhook from external services.

    Returns a JSON response with a single key "status" set to "ok".
    """
    payload = await request.json()
    if LOG_PAYLOADS:
        logger.info("Webhook payload: %s", redact_payload(payload))
    inbound = extract_inbound_message(payload)

    if not inbound or "@g.us" in inbound.chat_id:
        return {"status": "ok"}

    persist_inbound_event(inbound)

    if inbound.message_type == "text" and inbound.text:
        await buffer_message(
            chat_id=inbound.chat_id,
            message=inbound.text,
            message_id=inbound.message_id,
        )
    elif inbound.message_type in ("image", "document") and inbound.media_base64:
        await process_inbound_media(inbound)

    return {"status": "ok"}
