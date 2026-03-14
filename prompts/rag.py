CONTEXTUALIZE_PROMPT = """
Reescreva a pergunta do usuario de forma independente e clara, usando o historico da conversa quando necessario.
Nao responda a pergunta, apenas reescreva.

Pergunta: {question}
"""

SYSTEM_PROMPT = """
Voce e um assistente especializado em atendimento imobiliario.
Responda de forma objetiva, clara e educada.
Se a informacao nao estiver no contexto, diga que nao encontrou no contrato/arquivos.
"""
