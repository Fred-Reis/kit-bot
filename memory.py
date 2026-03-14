from langchain_community.chat_message_histories import RedisChatMessageHistory

from config import REDIS_URL


def get_session_history(session_id):
    """
    Returns a RedisChatMessageHistory object associated with a given session id.

    The returned object is responsible for storing and retrieving chat history
    messages associated with the given session id.

    :param session_id: The session id to retrieve the chat history from.
    :return: A RedisChatMessageHistory object associated with the given session id.
    """
    return RedisChatMessageHistory(
        session_id=session_id,
        url=REDIS_URL,
    )
