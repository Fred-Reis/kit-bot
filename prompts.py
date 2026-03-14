from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from prompts.rag import CONTEXTUALIZE_PROMPT, SYSTEM_PROMPT

contextualize_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", CONTEXTUALIZE_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ]
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ]
)
