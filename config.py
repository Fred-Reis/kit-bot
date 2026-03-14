"""module to declare env vars"""

import os

from dotenv import load_dotenv


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")
OPENAI_MODEL_TEMPERATURE = os.getenv("OPENAI_MODEL_TEMPERATURE")

VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH")
RAG_FILES_DIR = os.getenv("RAG_FILES_DIR")

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME")
EVOLUTION_AUTHENTICATION_API_KEY = os.getenv("AUTHENTICATION_API_KEY")

CACHE_REDIS_URI = os.getenv("AUTHENTICATION_API_KEY")

REDIS_URL = os.getenv("CACHE_REDIS_URI")

BUFFER_KEY_SUFFIX = os.getenv("BUFFER_KEY_SUFFIX")
BUFFER_TTL = os.getenv("BUFFER_TTL")
DEBOUNCE_SECONDS = os.getenv("DEBOUNCE_SECONDS")

DATABASE_URL = os.getenv("DATABASE_URL")

AUTO_CREATE_DB = os.getenv("AUTO_CREATE_DB", "false").lower() == "true"
LOG_PAYLOADS = os.getenv("LOG_PAYLOADS", "false").lower() == "true"

MEDIA_DIR = os.getenv("MEDIA_DIR", "media")
