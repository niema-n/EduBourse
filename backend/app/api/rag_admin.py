"""Authenticated, non-destructive RAG maintenance entry point for J9 n8n."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.rag.chunking import ChunkRecord
from app.rag.domain_policy import CorpusDocumentManifest

router = APIRouter(tags=["RAG Administration"])

UpdateMode = Literal["validate", "incremental_update"]
APPROVED_SOURCE = "local_approved_corpus"


class RagUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    mode: UpdateMode = "validate"
    source: Literal["local_approved_corpus"] = APPROVED_SOURCE


class RagUpdateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["ok"]
    mode: UpdateMode
    source: Literal["local_approved_corpus"]
    sources_checked: int = Field(ge=0)
    documents_changed: int = Field(ge=0)
    chunks_added: int = Field(ge=0)
    chunks_updated: int = Field(ge=0)
    chunks_unchanged: int = Field(ge=0)


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _validate_local_corpus(root: Path) -> tuple[int, int]:
    manifest_path = root / "backend/data/rag/manifests/corpus_v1.json"
    chunks_path = root / "backend/data/rag/processed/chunks_v1.jsonl"
    if not manifest_path.is_file() or not chunks_path.is_file():
        raise RuntimeError("approved local corpus artifacts are unavailable")

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = [
        CorpusDocumentManifest.model_validate(item) for item in manifest_payload["documents"]
    ]
    if not documents or any(document.authority == "internal_approved" for document in documents):
        raise RuntimeError("approved corpus manifest is invalid")

    chunks = [
        ChunkRecord.model_validate_json(line)
        for line in chunks_path.read_text(encoding="utf-8").splitlines()
    ]
    if len(chunks) != 400 or len({chunk.chunk_id for chunk in chunks}) != 400:
        raise RuntimeError("approved corpus chunk artifact is invalid")
    chunks_hash = hashlib.sha256(chunks_path.read_bytes()).hexdigest()
    if chunks_hash != (
        "62d76b117a2273ba3fd2ddbc2cf32a5fdb72ced468e1cf6b2097a2322a4346e1"
    ):
        raise RuntimeError("approved corpus chunk artifact hash mismatch")
    return len({document.authority for document in documents}), len(chunks)


def _authorize(token: str | None) -> None:
    expected = get_settings().edubourse_n8n_internal_token.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG administration is not configured",
        )
    if token is None or not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid internal authorization",
        )


@router.post(
    "/admin/rag/update",
    response_model=RagUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate the approved local RAG corpus",
    operation_id="admin_rag_update",
    responses={
        401: {"description": "Invalid internal authorization"},
        503: {"description": "RAG administration unavailable"},
    },
)
def update_rag(
    payload: RagUpdateRequest,
    x_edubourse_internal_token: str | None = Header(default=None),
) -> RagUpdateResponse:
    _authorize(x_edubourse_internal_token)
    try:
        sources_checked, chunk_count = _validate_local_corpus(_repository_root())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="approved corpus validation failed",
        ) from exc
    return RagUpdateResponse(
        status="ok",
        mode=payload.mode,
        source=payload.source,
        sources_checked=sources_checked,
        documents_changed=0,
        chunks_added=0,
        chunks_updated=0,
        chunks_unchanged=chunk_count,
    )
