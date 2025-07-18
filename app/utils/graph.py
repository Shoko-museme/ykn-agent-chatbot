"""This file contains the graph utilities for the application."""

import tiktoken
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import trim_messages as _trim_messages

from app.core.config import settings
from app.schemas import Message


def dump_messages(messages: list[Message]) -> list[dict]:
    """Dump the messages to a list of dictionaries.

    Args:
        messages (list[Message]): The messages to dump.

    Returns:
        list[dict]: The dumped messages.
    """
    return [message.model_dump() for message in messages]


def _get_token_count(messages: list[dict], encoding: tiktoken.Encoding) -> int:
    """Get the token count of a list of messages."""
    return sum(len(encoding.encode(str(item))) for item in messages)


def prepare_messages(messages: list[Message], llm: BaseChatModel, system_prompt: str) -> list[Message]:
    """Prepare the messages for the LLM.

    Args:
        messages (list[Message]): The messages to prepare.
        llm (BaseChatModel): The LLM to use.
        system_prompt (str): The system prompt to use.

    Returns:
        list[Message]: The prepared messages.
    """
    # Get the encoding for the model
    try:
        encoding = tiktoken.encoding_for_model(llm.model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    # Create a token counter function
    token_counter = lambda msgs: _get_token_count(msgs, encoding)

    trimmed_messages = _trim_messages(
        dump_messages(messages),
        strategy="last",
        token_counter=token_counter,
        max_tokens=settings.MAX_TOKENS,
        start_on="human",
        include_system=False,
        allow_partial=False,
    )
    return [Message(role="system", content=system_prompt)] + trimmed_messages
