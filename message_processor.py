def log(*args):
    """
    Prints a message to the console with a "[PROCESSOR]" prefix.

    Args:
        *args: The message to be printed.
    """
    print("[PROCESSOR]", *args)


async def process_grouped_message(chat_id: str, message: str) -> None:
    """
    Process a grouped message after debounce.

    This is the central processing point. Router integration will be added here.
    """
    log(f"Processing grouped message for {chat_id}: {message}")
    # TODO: route message
