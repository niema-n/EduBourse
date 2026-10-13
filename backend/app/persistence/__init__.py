"""Optional persistence foundation, disabled by default."""

from app.persistence.checkpointer import (
    PersistentPostgresCheckpointer,
    create_graph_checkpointer,
)
from app.persistence.conversation_history_store import SqlAlchemyConversationHistoryStore
from app.persistence.database import (
    PersistenceConfigurationError,
    PersistenceDatabase,
    PersistenceDisabledError,
    PersistenceUnavailableError,
)
from app.persistence.models import (
    ConversationMessageRecord,
    ConversationThreadRecord,
    LearningProfileRecord,
)
from app.persistence.thread_store import ConversationThreadStore

__all__ = [
    "ConversationThreadRecord",
    "ConversationMessageRecord",
    "ConversationThreadStore",
    "PersistentPostgresCheckpointer",
    "create_graph_checkpointer",
    "LearningProfileRecord",
    "SqlAlchemyConversationHistoryStore",
    "PersistenceConfigurationError",
    "PersistenceDatabase",
    "PersistenceDisabledError",
    "PersistenceUnavailableError",
]
