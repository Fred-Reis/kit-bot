from openai import OpenAIError
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from config import OPENAI_MODEL_NAME
from logger import get_logger
from prompts.lead import LEAD_REPLY_PROMPT

logger = get_logger("lead_responder")


def generate_lead_reply(facts: dict) -> str:
    model_name = OPENAI_MODEL_NAME or "gpt-4o-mini"
    llm = ChatOpenAI(model=model_name, temperature=0, max_tokens=256)
    chain = LEAD_REPLY_PROMPT | llm | StrOutputParser()
    try:
        response = chain.invoke(facts)
    except OpenAIError as exc:
        logger.exception("Failed to generate lead reply: %s", exc)
        return "Recebi sua mensagem. Vamos seguir com o cadastro."
    return response.strip()
