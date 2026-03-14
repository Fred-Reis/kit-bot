import re

import requests
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db import SessionLocal
from evolution_api import send_whatsapp_message
from logger import get_logger
from messages import lead as lead_messages
from models import Conversation, Event, Profile, User

logger = get_logger("lead_flow")


def normalize_whatsapp_number(chat_id: str) -> str:
    if "@" in chat_id:
        return chat_id.split("@", 1)[0]
    return chat_id


def extract_cpf(text: str) -> str | None:
    match = re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", text)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    return digits if len(digits) == 11 else None


def extract_email(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None


def extract_income(text: str) -> str | None:
    match = re.search(r"\d[\d\.,]+", text)
    if not match:
        return None
    raw = match.group(0)
    return raw.replace(".", "").replace(",", ".")


def extract_name(text: str) -> str | None:
    cleaned = re.sub(r"[^A-Za-z\s]", " ", text)
    parts = [p for p in cleaned.split() if len(p) > 1]
    if len(parts) >= 2:
        return " ".join(parts)
    return None


def apply_profile_updates(
    message: str,
    context: dict,
    user: User | None,
    profile: Profile | None,
) -> None:
    cpf = extract_cpf(message)
    name = extract_name(message)

    if cpf:
        context["cpf"] = cpf
        if profile:
            profile.cpf = cpf
    if name:
        context["name"] = name
        if user and not user.name:
            user.name = name


def apply_contact_updates(
    message: str,
    context: dict,
    profile: Profile | None,
) -> None:
    email = extract_email(message)
    income = extract_income(message)

    if email:
        context["email"] = email
        if profile:
            profile.email = email
    if income:
        context["income"] = income
        if profile:
            profile.income = income


def handle_start(message: str, context: dict, user: User | None, profile: Profile | None):
    apply_profile_updates(message, context, user, profile)
    has_cpf = bool(context.get("cpf"))
    has_name = bool(context.get("name"))

    if not has_cpf and not has_name:
        return "lead.await_profile", lead_messages.START
    if not has_cpf:
        return "lead.await_profile", lead_messages.MISSING_PROFILE_CPF
    if not has_name:
        return "lead.await_profile", lead_messages.MISSING_PROFILE_NAME
    return "lead.await_contact", lead_messages.CONTACT


def handle_profile(message: str, context: dict, user: User | None, profile: Profile | None):
    apply_profile_updates(message, context, user, profile)
    has_cpf = bool(context.get("cpf"))
    has_name = bool(context.get("name"))

    if not has_cpf and not has_name:
        return "lead.await_profile", lead_messages.MISSING_PROFILE_BOTH
    if not has_cpf:
        return "lead.await_profile", lead_messages.MISSING_PROFILE_CPF
    if not has_name:
        return "lead.await_profile", lead_messages.MISSING_PROFILE_NAME
    return "lead.await_contact", lead_messages.CONTACT


def handle_contact(message: str, context: dict, profile: Profile | None):
    apply_contact_updates(message, context, profile)
    has_email = bool(context.get("email"))
    has_income = bool(context.get("income"))

    if not has_email:
        return "lead.await_contact", lead_messages.CONTACT_MISSING_EMAIL
    if not has_income:
        return "lead.await_contact", lead_messages.CONTACT_MISSING_INCOME
    return "lead.await_documents", lead_messages.DOCS


def handle_documents(message: str, context: dict):
    return "lead.await_documents", lead_messages.WAIT_DOCS


def handle_fallback(message: str, context: dict):
    return "lead.await_profile", lead_messages.FALLBACK


STATE_HANDLERS = {
    "lead.start": handle_start,
    "lead.await_profile": handle_profile,
    "lead.await_contact": handle_contact,
    "lead.await_documents": handle_documents,
}


async def handle_lead_message(chat_id: str, message: str, user_id: int | None) -> None:
    logger.info("Lead message received for %s", chat_id)
    reply_text = None

    db = SessionLocal()
    try:
        user = db.get(User, user_id) if user_id else None
        conversation = db.execute(
            select(Conversation).where(Conversation.chat_id == chat_id)
        ).scalar_one_or_none()
        if not conversation:
            conversation = Conversation(
                chat_id=chat_id,
                state="lead.start",
                context_json={},
            )
            db.add(conversation)

        profile = None
        if user_id:
            profile = db.execute(
                select(Profile).where(Profile.user_id == user_id)
            ).scalar_one_or_none()
            if not profile:
                profile = Profile(user_id=user_id)
                db.add(profile)

        state = conversation.state or "lead.start"
        context = dict(conversation.context_json or {})

        handler = STATE_HANDLERS.get(state, handle_fallback)
        if handler in (handle_start, handle_profile):
            new_state, reply_text = handler(message, context, user, profile)
        elif handler is handle_contact:
            new_state, reply_text = handler(message, context, profile)
        else:
            new_state, reply_text = handler(message, context)

        conversation.state = new_state
        conversation.context_json = context

        event = Event(
            user_id=user_id,
            chat_id=chat_id,
            type="lead.received",
            payload_json={
                "message": message,
                "state": state,
                "new_state": new_state,
            },
        )
        db.add(event)
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to persist lead event: %s", exc)
        reply_text = None
    finally:
        db.close()

    if reply_text:
        try:
            send_whatsapp_message(normalize_whatsapp_number(chat_id), reply_text)
        except requests.RequestException as exc:
            logger.exception("Failed to send lead reply: %s", exc)
