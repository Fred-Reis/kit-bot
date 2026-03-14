"""evolution api module"""

import requests

from config import (
    EVOLUTION_API_URL,
    EVOLUTION_INSTANCE_NAME,
    EVOLUTION_AUTHENTICATION_API_KEY,
)


def send_whatsapp_message(number, text):
    """
    Send a WhatsApp message to a given number.

    Parameters
    ----------
    number : str
        The number to send the message to.
    text : str
        The text to send.

    Returns
    -------
    response : requests.Response
        The response from the Evolution API.
    """
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_AUTHENTICATION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": number,
        "text": text,
    }
    requests.post(
        url=url,
        json=payload,
        headers=headers,
        timeout=3000,
    )
