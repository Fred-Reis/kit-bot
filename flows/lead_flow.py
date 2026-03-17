import re

import requests
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from db import SessionLocal
from evolution_api import send_whatsapp_message
from logger import get_logger
from models import Conversation, Document, Event, Profile, User
from services.lead_agent import extract_lead_update
from services.property_catalog import (
    find_property_by_reference,
    list_available_properties,
    serialize_property,
    summarize_property,
)
from services.lead_responder import generate_lead_reply

logger = get_logger("lead_flow")

DOCS_REQUIRED_COUNT = {"cnh": 2, "rg_cpf": 3}
DOCS_RULES = {
    "cnh_images_required": 2,
    "rg_cpf_images_required": 3,
}


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


def apply_profile_updates(
    message: str,
    context: dict,
    user: User | None,
    profile: Profile | None,
) -> None:
    cpf = extract_cpf(message)

    if cpf:
        context["cpf"] = cpf
        if profile:
            profile.cpf = cpf

    explicit_name = context.get("name")
    if explicit_name and user and not user.name:
        user.name = explicit_name


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


def build_known_context(
    name_value: str,
    interest: str | None,
    property_interest: str | None,
    property_reference: str | None,
    cpf: str | None,
    email: str | None,
    income: str | None,
    docs_preference: str | None,
    docs_received_count: int,
    available_properties_count: int,
) -> str:
    parts = []
    if name_value:
        parts.append(f"Nome conhecido: {name_value}.")
    else:
        parts.append("Nome ainda nao informado.")

    if interest == "yes":
        parts.append("A pessoa demonstrou interesse em locacao.")
    elif interest == "no":
        parts.append("A pessoa disse que nao tem interesse no momento.")
    else:
        parts.append("Ainda nao sabemos se ha interesse em algum imovel.")

    if property_interest:
        parts.append(f"Imovel de interesse informado: {property_interest}.")
    else:
        parts.append("Imovel de interesse ainda nao informado.")

    if property_reference:
        parts.append(f"Referencia mencionada: {property_reference}.")

    if available_properties_count:
        parts.append(
            f"Temos {available_properties_count} imovel(is) desocupado(s) no catalogo."
        )
    else:
        parts.append("Nao ha imoveis desocupados no catalogo neste momento.")

    if cpf:
        parts.append("CPF ja informado.")
    if email:
        parts.append("E-mail ja informado.")
    if income:
        parts.append("Renda ja informada.")
    if docs_preference:
        parts.append(f"Tipo de documento escolhido: {docs_preference}.")
    if docs_received_count:
        parts.append(f"Ja recebemos {docs_received_count} imagem(ns) de documento.")

    return " ".join(parts)


async def handle_lead_message(
    chat_id: str,
    message: str | None,
    user_id: int | None,
    media: dict | None = None,
) -> None:
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
        previous_reply = context.get("last_bot_reply", "")

        message_text = message or ""
        context["wants_pause"] = False
        context["wants_human"] = False
        context["wants_available_properties"] = False
        context["wants_property_details"] = False
        updates = extract_lead_update(message_text, context)
        context.update(updates)

        apply_profile_updates(message_text, context, user, profile)
        apply_contact_updates(message_text, context, profile)

        available_properties = list_available_properties(db)
        available_properties_summary = (
            "; ".join(summarize_property(property_obj) for property_obj in available_properties)
            if available_properties
            else "Nenhum imovel desocupado disponivel no momento."
        )
        available_properties_count = len(available_properties)

        property_reference = context.get("property_reference")
        looked_up_property = find_property_by_reference(db, property_reference)
        property_lookup_status = "none"
        selected_property_details = ""
        if property_reference:
            if looked_up_property is None:
                property_lookup_status = "not_found"
            else:
                serialized_property = serialize_property(looked_up_property)
                selected_property_details = str(serialized_property)
                if looked_up_property.status == "vacant":
                    property_lookup_status = "available"
                    context["property_interest"] = (
                        looked_up_property.title or looked_up_property.reference
                    )
                else:
                    property_lookup_status = "unavailable"

        if (
            context.get("interest") is None
            and (
                property_reference
                or bool(context.get("wants_available_properties"))
                or context.get("question_topic") == "property"
            )
        ):
            context["interest"] = "yes"

        docs_preference = context.get("docs_preference")
        docs_required_count = DOCS_REQUIRED_COUNT.get(docs_preference, 0)

        docs_received_count = 0
        if user_id:
            count_stmt = (
                select(func.count())  # pylint: disable=not-callable
                .select_from(Document)
                .where(Document.user_id == user_id)
            )
            docs_received_count = db.execute(count_stmt).scalar_one() or 0

        if media and media.get("path") and user_id:
            document = Document(
                user_id=user_id,
                type=media.get("type"),
                status="received",
                path=media.get("path"),
                extracted_json={
                    "mime": media.get("mime"),
                    "message_id": media.get("message_id"),
                    "docs_preference": docs_preference,
                },
            )
            db.add(document)
            docs_received_count += 1

        docs_missing_count = max(0, docs_required_count - docs_received_count)

        missing_fields = []
        name_value = context.get("name") or (user.name if user else "")
        interest = context.get("interest")
        property_interest = context.get("property_interest")
        user_intent = context.get("user_intent", "unknown")
        question_topic = context.get("question_topic")
        wants_pause = bool(context.get("wants_pause"))
        wants_human = bool(context.get("wants_human"))
        wants_available_properties = bool(context.get("wants_available_properties"))
        wants_property_details = bool(context.get("wants_property_details"))
        should_offer_properties = any(
            [
                wants_available_properties,
                wants_property_details,
                bool(property_reference),
                question_topic == "property",
                interest == "yes",
            ]
        )

        if wants_pause:
            journey_phase = "pause"
            new_state = "lead.paused"
        elif wants_human:
            journey_phase = "handoff"
            new_state = "lead.handoff"
        elif interest is None:
            journey_phase = "abertura"
            new_state = "lead.ask_interest"
        elif interest == "no":
            journey_phase = "sem_interesse"
            new_state = "lead.no_interest"
        elif property_lookup_status == "not_found":
            journey_phase = "imovel"
            new_state = "lead.property_not_found"
        elif property_lookup_status == "unavailable":
            journey_phase = "imovel"
            new_state = "lead.property_unavailable"
        elif not property_interest:
            journey_phase = "imovel"
            new_state = "lead.ask_property"
        else:
            if not name_value:
                missing_fields.append("nome")
            if not context.get("cpf"):
                missing_fields.append("CPF")
            if not context.get("email"):
                missing_fields.append("e-mail")
            if not context.get("income"):
                missing_fields.append("renda mensal aproximada")

            if missing_fields:
                journey_phase = "pre_cadastro"
                new_state = "lead.collect_basic"
            elif not docs_preference:
                journey_phase = "documentacao"
                new_state = "lead.choose_docs"
            elif docs_missing_count > 0:
                journey_phase = "documentacao"
                new_state = "lead.collect_docs"
            else:
                journey_phase = "analise"
                new_state = "lead.done"

        known_context = build_known_context(
            name_value=name_value,
            interest=interest,
            property_interest=property_interest,
            property_reference=property_reference,
            cpf=context.get("cpf"),
            email=context.get("email"),
            income=context.get("income"),
            docs_preference=docs_preference,
            docs_received_count=docs_received_count,
            available_properties_count=available_properties_count,
        )

        event = Event(
            user_id=user_id,
            chat_id=chat_id,
            type="lead.received",
            payload_json={
                "message": message,
                "state": state,
                "new_state": new_state,
                "media": media,
            },
        )
        db.add(event)
        db.commit()

        facts = {
            "journey_phase": journey_phase,
            "known_context": known_context,
            "name": name_value,
            "interest": interest,
            "property_interest": property_interest or "",
            "property_reference": property_reference or "",
            "property_lookup_status": property_lookup_status,
            "selected_property_details": selected_property_details,
            "available_properties_summary": available_properties_summary,
            "available_properties_count": available_properties_count,
            "wants_available_properties": wants_available_properties,
            "wants_property_details": wants_property_details,
            "should_offer_properties": should_offer_properties,
            "user_intent": user_intent,
            "question_topic": question_topic or "unknown",
            "missing_fields": ", ".join(missing_fields) if missing_fields else "nenhum",
            "docs_preference": docs_preference or "",
            "docs_received_count": docs_received_count,
            "docs_missing_count": docs_missing_count,
            "docs_rules": DOCS_RULES,
            "actions_available": {
                "can_pause": True,
                "can_handoff": True,
            },
            "media_received": bool(media),
            "last_message": message_text,
            "previous_reply": previous_reply,
        }
        reply_text = generate_lead_reply(facts)

        conversation.state = new_state
        conversation.context_json = {
            **context,
            "docs_received_count": docs_received_count,
            "last_bot_reply": reply_text,
            "last_user_message": message_text,
        }
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
