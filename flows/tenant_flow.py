from sqlalchemy.exc import SQLAlchemyError

from db import SessionLocal
from logger import get_logger
from models import Event

logger = get_logger("tenant_flow")


async def handle_tenant_message(
    chat_id: str,
    message: str | None,
    user_id: int | None,
    media: dict | None = None,
) -> None:
    logger.info("Tenant message received for %s", chat_id)

    db = SessionLocal()
    try:
        event = Event(
            user_id=user_id,
            chat_id=chat_id,
            type="tenant.received",
            payload_json={"message": message, "media": media},
        )
        db.add(event)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to persist tenant event: %s", exc)
    finally:
        db.close()
