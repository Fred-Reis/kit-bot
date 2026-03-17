from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

EXTRACT_LEAD_PROMPT = PromptTemplate.from_template(
    """
Extraia dados da mensagem do usuario e retorne JSON estrito com as chaves abaixo.

Chaves:
- name: string | null
- name_is_explicit: boolean
- interest: "yes" | "no" | null
- property_interest: string | null
- property_reference: string | null
- cpf: string | null
- email: string | null
- income: string | null
- docs_preference: "cnh" | "rg_cpf" | null
- user_intent: "greeting" | "question" | "provide_info" | "continue" | "pause" | "human_help" | "objection" | "insult" | "unknown"
- question_topic: "process" | "property" | "documents" | "status" | "unknown" | null
- wants_available_properties: boolean
- wants_property_details: boolean
- wants_pause: boolean
- wants_human: boolean

Regras:
- Nao invente. Use null/false se nao estiver claro.
- So preencha name quando a pessoa realmente se identificar. Nesses casos, marque name_is_explicit como true.
- Se a pessoa nao falou o proprio nome de forma clara, deixe name como null e name_is_explicit como false.
- Se a mensagem citar uma referencia de imovel como KIT-01 ou APT-02, preencha property_reference.
- Se a mensagem for apenas cumprimento, reclamacao, provocacao ou pergunta, nao preencha campos irrelevantes.
- Se a pessoa escolher CNH ou RG+CPF, preencha docs_preference.
- Mantenha o contexto atual.

Mensagem: {message}
Contexto atual (JSON): {context}
"""
)

PARSER = JsonOutputParser()
