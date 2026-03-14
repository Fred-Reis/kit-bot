from logger import get_logger

logger = get_logger("processor")


async def process_grouped_message(chat_id: str, message: str) -> None:
    """
    Process a grouped message after debounce.

    This is the central processing point. Router integration will be added here.
    """
    logger.info("Processing grouped message for %s: %s", chat_id, message)
    # TODO: route message
