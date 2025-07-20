"""This file contains the schemas for the application."""

from app.schemas.auth import Token
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)
from app.schemas.graph import GraphState
from app.schemas.task import (
    FormExtractionRequest,
    FormExtractionSyncResponse,
    FormExtractionAsyncResponse,
    FormExtractionTaskStatus,
    FormExtractionError,
)

__all__ = [
    "Token",
    "ChatRequest",
    "ChatResponse",
    "Message",
    "StreamResponse",
    "GraphState",
    "FormExtractionRequest",
    "FormExtractionSyncResponse",
    "FormExtractionAsyncResponse",
    "FormExtractionTaskStatus",
    "FormExtractionError",
]
