import json

from langchain_openai import ChatOpenAI

from config import OPENAI_MODEL_NAME
from logger import get_logger
from prompts.lead_extractor import EXTRACT_LEAD_PROMPT, PARSER

logger = get_logger("lead_agent")


def _normalize_interest(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    if value in ("yes", "sim", "s"):
        return "yes"
    if value in ("no", "nao", "não", "n"):
        return "no"
    return None


def _normalize_docs_preference(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    if value in ("cnh", "carteira"):
        return "cnh"
    if value in ("rg_cpf", "rg", "cpf"):
        return "rg_cpf"
    return None


def _normalize_user_intent(value: str | None) -> str:
    if not value:
        return "unknown"
    value = value.strip().lower()
    allowed = {
        "greeting",
        "question",
        "provide_info",
        "continue",
        "pause",
        "human_help",
        "objection",
        "insult",
        "unknown",
    }
    return value if value in allowed else "unknown"


def _normalize_question_topic(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    allowed = {"process", "property", "documents", "status", "unknown"}
    return value if value in allowed else "unknown"


def _normalize_property_reference(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().upper()
    return normalized or None


def extract_lead_update(message: str, context: dict) -> dict:
    llm = ChatOpenAI(
        model=OPENAI_MODEL_NAME or "gpt-4o-mini",
        temperature=0,
        max_tokens=256,
    )
    chain = EXTRACT_LEAD_PROMPT | llm | PARSER
    try:
        raw = chain.invoke(
            {
                "message": message,
                "context": json.dumps(context, ensure_ascii=False),
            }
        ) or {}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to extract lead updates: %s", exc)
        return {}

    updates = {}
    name = raw.get("name")
    if raw.get("name_is_explicit") is True and name:
        updates["name"] = name.strip()

    interest = _normalize_interest(raw.get("interest"))
    if interest:
        updates["interest"] = interest

    prop = raw.get("property_interest")
    if prop:
        updates["property_interest"] = prop.strip()

    property_reference = _normalize_property_reference(raw.get("property_reference"))
    if property_reference:
        updates["property_reference"] = property_reference

    cpf = raw.get("cpf")
    if cpf:
        updates["cpf"] = cpf.strip()

    email = raw.get("email")
    if email:
        updates["email"] = email.strip()

    income = raw.get("income")
    if income:
        updates["income"] = income.strip()

    pref = _normalize_docs_preference(raw.get("docs_preference"))
    if pref:
        updates["docs_preference"] = pref

    updates["user_intent"] = _normalize_user_intent(raw.get("user_intent"))
    updates["question_topic"] = _normalize_question_topic(raw.get("question_topic"))

    if raw.get("wants_pause") is True:
        updates["wants_pause"] = True
    if raw.get("wants_human") is True:
        updates["wants_human"] = True
    if raw.get("wants_available_properties") is True:
        updates["wants_available_properties"] = True
    if raw.get("wants_property_details") is True:
        updates["wants_property_details"] = True

    return updates
