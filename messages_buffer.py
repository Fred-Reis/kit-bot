"""Buffer module"""

import asyncio
from collections import defaultdict

import redis.asyncio as redis

from config import (
    BUFFER_KEY_SUFFIX,
    BUFFER_TTL,
    DEBOUNCE_SECONDS,
    REDIS_URL,
)
from message_processor import process_grouped_message

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)
debounce_tasks = defaultdict(asyncio.Task)
BUFFER_TTL_SECONDS = int(BUFFER_TTL) if BUFFER_TTL else 3600


def log(*args):
    """
    Prints a message to the console with a "[BUFFER]" prefix.

    Args:
        *args: The message to be printed.
    """
    print("[BUFFER]", *args)


async def is_duplicate_message(chat_id: str, message_id: str | None) -> bool:
    """
    Returns True if the message has already been processed.
    """
    if not message_id:
        return False

    dedupe_key = f"{chat_id}:dedupe:{message_id}"
    was_set = await redis_client.set(
        dedupe_key,
        "1",
        ex=BUFFER_TTL_SECONDS,
        nx=True,
    )
    return not was_set


async def buffer_message(chat_id: str, message: str, message_id: str | None = None):
    """
    Buffers a message for a given chat id.

    This function buffers a message for a given chat id, and then sets up a task
    to handle the debounce.

    If there is already a task for the given chat id, that task is cancelled,
    and a new one is created.

    :param chat_id: The chat id to buffer the message for.
    :param message: The message to be buffered.
    :param message_id: The message id for idempotency.
    """
    if await is_duplicate_message(chat_id, message_id):
        log(f"Duplicate message ignored for {chat_id}: {message_id}")
        return

    buffer_key = f"{chat_id}{BUFFER_KEY_SUFFIX}"

    await redis_client.rpush(buffer_key, message)
    await redis_client.expire(buffer_key, BUFFER_TTL_SECONDS)

    log(f"Added buffer message from {chat_id}: {message}")

    if debounce_tasks.get(chat_id):
        debounce_tasks[chat_id].cancel()
        log(f"Cleared debounce for: {chat_id}")

    debounce_tasks[chat_id] = asyncio.create_task(handle_debounce(chat_id))


async def handle_debounce(chat_id: str):
    """
    Handles debouncing for a given chat id.

    This function is responsible for sleeping for a given amount of time (DEBOUNCE_SECONDS),
    and then sending the grouped messages to the LLM for processing.

    :param chat_id: The chat id to handle the debounce for.
    """
    try:
        log(f"Debounce initialized to {chat_id}")
        await asyncio.sleep(float(DEBOUNCE_SECONDS))

        buffer_key = f"{chat_id}{BUFFER_KEY_SUFFIX}"
        messages = await redis_client.lrange(buffer_key, 0, -1)

        full_message = " ".join(messages).strip()

        if full_message:
            log(f"Sending grouped messages to processor from: {chat_id} - {full_message}")
            await process_grouped_message(chat_id, full_message)

        await redis_client.delete(buffer_key)

    except asyncio.CancelledError:
        log(f"Debouncing canceled to: {chat_id}")

