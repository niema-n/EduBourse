from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import chromadb

from app.config import get_settings

ChromaStatus = Literal["ok", "unavailable"]
CollectionStatus = Literal["present", "missing", "unknown"]


@dataclass(frozen=True)
class ChromaCheck:
    status: ChromaStatus
    collection_status: CollectionStatus = "unknown"
    document_count: int = 0


@lru_cache
def get_chroma_client():
    settings = get_settings()
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def check_chroma() -> ChromaCheck:
    settings = get_settings()
    try:
        client = get_chroma_client()
        client.heartbeat()
        try:
            collection = client.get_collection(settings.chroma_collection)
        except Exception:
            return ChromaCheck(status="ok", collection_status="missing", document_count=0)
        return ChromaCheck(
            status="ok",
            collection_status="present",
            document_count=collection.count(),
        )
    except Exception:
        return ChromaCheck(status="unavailable", collection_status="unknown", document_count=0)
