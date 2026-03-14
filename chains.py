from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory

from config import (
    OPENAI_MODEL_NAME,
    OPENAI_MODEL_TEMPERATURE,
)
from memory import get_session_history
from prompts import contextualize_prompt, qa_prompt
from vectorstore import get_vectorstore


def build_history_aware_retriever(llm, retriever):
    """
    Substitui create_history_aware_retriever
    """
    contextualize_chain = contextualize_prompt | llm | StrOutputParser()

    def get_relevant_docs(input_dict):
        if input_dict.get("chat_history"):
            search_query = contextualize_chain.invoke(input_dict)
        else:
            search_query = input_dict["question"]
        return retriever.invoke(search_query)

    return RunnableLambda(get_relevant_docs)


def build_qa_chain(llm):
    """
    Substitui create_stuff_documents_chain
    """

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    return (
        {
            "context": lambda x: format_docs(x["context"]),
            "question": lambda x: x["question"],
            "chat_history": lambda x: x.get("chat_history", []),
        }
        | qa_prompt
        | llm
        | StrOutputParser()
    )


def get_rag_chain():
    """
    Substitui create_retrieval_chain
    """
    llm = ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        temperature=OPENAI_MODEL_TEMPERATURE,
    )

    retriever = get_vectorstore().as_retriever()
    history_aware_retriever = build_history_aware_retriever(llm, retriever)
    qa_chain = build_qa_chain(llm)

    rag_chain = RunnablePassthrough.assign(
        context=history_aware_retriever
    ) | RunnablePassthrough.assign(answer=qa_chain)

    return rag_chain


def get_conversational_rag_chain():
    rag_chain = get_rag_chain()
    return RunnableWithMessageHistory(
        runnable=rag_chain,
        get_session_history=get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )
