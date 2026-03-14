import base64
import binascii
import hashlib
import mimetypes
import os

from config import MEDIA_DIR
from logger import get_logger

logger = get_logger("media_store")


def _strip_data_uri(value: str) -> str:
    if "," in value:
        return value.split(",", 1)[1]
    return value


def save_base64_media(base64_content: str, mime: str | None, message_id: str | None) -> str:
    if not base64_content:
        raise ValueError("Empty base64 content")

    cleaned = _strip_data_uri(base64_content)
    try:
        binary = base64.b64decode(cleaned)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 content") from exc

    digest = hashlib.sha256(binary).hexdigest()
    extension = ""
    if mime:
        extension = mimetypes.guess_extension(mime) or ""
    if not extension:
        extension = ".bin"

    filename = digest
    if message_id:
        filename = f"{message_id}_{digest}"

    os.makedirs(MEDIA_DIR, exist_ok=True)
    path = os.path.join(MEDIA_DIR, f"{filename}{extension}")

    if not os.path.exists(path):
        with open(path, "wb") as file_handle:
            file_handle.write(binary)
        logger.info("Saved media to %s", path)
    else:
        logger.info("Media already exists at %s", path)

    return path
