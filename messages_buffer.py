"""Buffer module"""

import asyncio
from collections import defaultdict

import redis.asyncio as redis

from chains import get_conversational_rag_chain
from config import (
    BUFFER_KEY_SUFFIX,
    BUFFER_TTL,
    DEBOUNCE_SECONDS,
    REDIS_URL,
)
from evolution_api import send_whatsapp_message

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)
convertional_rag_chain = get_conversational_rag_chain()
debounce_tasks = defaultdict(asyncio.Task)


def log(*args):
    """
    Prints a message to the console with a "[BUFFER]" prefix.

    Args:
        *args: The message to be printed.
    """
    print("[BUFFER]", *args)


async def buffer_message(chat_id: str, message: str):
    """
    Buffers a message for a given chat id.

    This function buffers a message for a given chat id, and then sets up a task
    to handle the debounce.

    If there is already a task for the given chat id, that task is cancelled,
    and a new one is created.

    :param chat_id: The chat id to buffer the message for.
    :param message: The message to be buffered.
    """
    buffer_key = f"{chat_id}{BUFFER_KEY_SUFFIX}"

    await redis_client.rpush(buffer_key, message)
    await redis_client.expire(buffer_key, BUFFER_TTL)

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
            log(f"Sending grouped messages to llm from: {chat_id} - {full_message}")
            # TODO: move this block to a separated function
            # Call router
            # TODO: Until here

        await redis_client.delete(buffer_key)

    except asyncio.CancelledError:
        log(f"Debouncing canceled to: {chat_id}")


def call_ai_service(message, chat_id):
    """
    Call the AI service to process the message.

    Parameters
    ----------
    message : str
        The message to be processed.

    Returns
    -------
    response : str
        The response from the AI service.


    """
    return convertional_rag_chain.invoke(
        input={"question": message},
        config={"configurable": {"session_id": chat_id}},
    )["answer"]
