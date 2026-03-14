from flows.router import route_message
from logger import get_logger
from schemas import InboundMessage
from services.media_store import save_base64_media

logger = get_logger("processor")


async def process_grouped_message(chat_id: str, message: str) -> None:
    """
    Process a grouped message after debounce.

    This is the central processing point. Router integration will be added here.
    """
    logger.info("Processing grouped message for %s: %s", chat_id, message)
    await route_message(chat_id, message)


async def process_inbound_media(inbound: InboundMessage) -> None:
    if not inbound.media_base64:
        logger.warning("Media payload missing base64 for %s", inbound.chat_id)
        return

    try:
        path = save_base64_media(
            base64_content=inbound.media_base64,
            mime=inbound.media_mime,
            message_id=inbound.message_id,
        )
    except ValueError as exc:
        logger.exception("Failed to decode media for %s: %s", inbound.chat_id, exc)
        return

    media = {
        "path": path,
        "mime": inbound.media_mime,
        "type": inbound.message_type,
        "message_id": inbound.message_id,
    }
    await route_message(inbound.chat_id, inbound.text, media)
