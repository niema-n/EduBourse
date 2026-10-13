"""Manifest-driven PDF page extraction for J6-03.

This module deliberately stops at page records. It does not chunk, index, or
call a provider. Source identity is copied from the frozen manifest verbatim.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pypdf import PdfReader

from app.rag.domain_policy import CorpusDocumentManifest

ExtractionStatus = Literal["ok", "empty", "low_text", "extraction_error"]


class ExtractedPageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    language: Literal["fr"]
    categories: list[str] = Field(min_length=1)
    page_number: int = Field(ge=1)
    page_count: int = Field(ge=1)
    document_hash: str = Field(min_length=64, max_length=64)
    text: str
    text_sha256: str = Field(min_length=64, max_length=64)
    raw_char_count: int = Field(ge=0)
    clean_char_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    extraction_status: ExtractionStatus
    warnings: list[str] = Field(default_factory=list)

    @field_validator("document_hash", "text_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("hash must be lowercase SHA-256")
        return value

    @field_validator("warnings")
    @classmethod
    def validate_warnings(cls, values: list[str]) -> list[str]:
        if any(not value or value not in ALLOWED_WARNINGS for value in values):
            raise ValueError("warnings must use controlled values")
        return values

    @model_validator(mode="after")
    def validate_page_and_text(self) -> ExtractedPageRecord:
        if self.page_number > self.page_count:
            raise ValueError("page_number must not exceed page_count")
        if self.clean_char_count != len(self.text):
            raise ValueError("clean_char_count must match text")
        if self.extraction_status == "empty" and self.text:
            raise ValueError("empty pages must have empty text")
        return self


ALLOWED_WARNINGS = frozenset(
    {"replacement_character", "control_characters_removed", "low_text", "extraction_error"}
)
LOW_TEXT_CHAR_LIMIT = 40


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_text(value: str) -> tuple[str, list[str]]:
    """Apply lossless structural cleanup without rewriting document content."""
    text = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    text = text.replace("\u00a0", " ")
    warnings: list[str] = []
    if "\ufffd" in text:
        warnings.append("replacement_character")
    cleaned_lines: list[str] = []
    removed_controls = False
    for line in text.split("\n"):
        safe_chars = []
        for char in line:
            if char in "\t" or unicodedata.category(char)[0] != "C":
                safe_chars.append(char)
            else:
                removed_controls = True
        cleaned_lines.append(re.sub(r"[ \t]+", " ", "".join(safe_chars)).strip())
    if removed_controls:
        warnings.append("control_characters_removed")
    while cleaned_lines and not cleaned_lines[0]:
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()
    compact_lines: list[str] = []
    blank_seen = False
    for line in cleaned_lines:
        if not line:
            if not blank_seen:
                compact_lines.append(line)
            blank_seen = True
        else:
            compact_lines.append(line)
            blank_seen = False
    return "\n".join(compact_lines), warnings


def _status(text: str, warnings: list[str]) -> ExtractionStatus:
    if not text.strip():
        return "empty"
    if len(text.strip()) < LOW_TEXT_CHAR_LIMIT:
        if "low_text" not in warnings:
            warnings.append("low_text")
        return "low_text"
    return "ok"


def _safe_source_path(repository_root: Path, manifest_path: str) -> Path:
    root = (repository_root / "backend" / "data" / "rag" / "raw").resolve()
    candidate = (repository_root / "backend" / manifest_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("manifest source path escapes approved raw corpus") from exc
    if candidate.suffix.casefold() != ".pdf" or not candidate.is_file():
        raise ValueError("manifest source path must be an existing PDF")
    return candidate


def _manifest(repository_root: Path, path: Path) -> tuple[list[CorpusDocumentManifest], str]:
    raw = path.read_bytes()
    manifest_hash = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw.decode("utf-8"))
    documents = [CorpusDocumentManifest(**entry) for entry in payload["documents"]]
    return documents, manifest_hash


def _page_record(
    document: CorpusDocumentManifest,
    page_number: int,
    page_count: int,
    document_hash: str,
    raw_text: str,
    *,
    extraction_error: str | None = None,
) -> ExtractedPageRecord:
    raw_char_count = len(raw_text)
    if extraction_error:
        text, warnings = "", ["extraction_error"]
        status: ExtractionStatus = "extraction_error"
    else:
        text, warnings = clean_text(raw_text)
        status = _status(text, warnings)
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ExtractedPageRecord(
        source_id=document.source_id,
        title=document.title,
        authority=document.authority,
        language=document.language,
        categories=list(document.category),
        page_number=page_number,
        page_count=page_count,
        document_hash=document_hash,
        text=text,
        text_sha256=text_hash,
        raw_char_count=raw_char_count,
        clean_char_count=len(text),
        word_count=len(text.split()),
        extraction_status=status,
        warnings=warnings,
    )


def extract_corpus(repository_root: Path) -> tuple[list[ExtractedPageRecord], dict[str, Any]]:
    manifest_path = repository_root / "backend/data/rag/manifests/corpus_v1.json"
    documents, manifest_hash = _manifest(repository_root, manifest_path)
    records: list[ExtractedPageRecord] = []
    document_results: list[dict[str, Any]] = []
    for document in sorted(documents, key=lambda item: item.source_id):
        result: dict[str, Any] = {
            "source_id": document.source_id,
            "page_count": 0,
            "pages_ok": 0,
            "pages_empty": 0,
            "pages_low_text": 0,
            "pages_error": 0,
            "raw_chars": 0,
            "clean_chars": 0,
            "words": 0,
            "warnings": [],
        }
        try:
            path = _safe_source_path(repository_root, document.file_path or "")
            actual_hash = sha256_file(path)
            if actual_hash != document.document_hash:
                result["warnings"] = ["SOURCE_HASH_MISMATCH"]
                result["error"] = "SOURCE_HASH_MISMATCH"
                document_results.append(result)
                continue
            reader = PdfReader(str(path), strict=True)
            page_count = len(reader.pages)
            result["page_count"] = page_count
            for index, page in enumerate(reader.pages, start=1):
                try:
                    raw_text = page.extract_text() or ""
                    record = _page_record(
                        document, index, page_count, actual_hash, raw_text
                    )
                except Exception as exc:  # one bad page must not stop the document
                    record = _page_record(
                        document,
                        index,
                        page_count,
                        actual_hash,
                        "",
                        extraction_error=type(exc).__name__,
                    )
                records.append(record)
                result["raw_chars"] += record.raw_char_count
                result["clean_chars"] += record.clean_char_count
                result["words"] += record.word_count
                counter_name = (
                    "pages_error"
                    if record.extraction_status == "extraction_error"
                    else f"pages_{record.extraction_status}"
                )
                result[counter_name] += 1
                result["warnings"].extend(record.warnings)
        except Exception as exc:
            result["warnings"] = [
                (
                    "SOURCE_HASH_MISMATCH"
                    if result.get("error") == "SOURCE_HASH_MISMATCH"
                    else type(exc).__name__
                )
            ]
            result["error"] = result.get("error", type(exc).__name__)
        result["warnings"] = sorted(set(result["warnings"]))
        document_results.append(result)
    records.sort(key=lambda record: (record.source_id, record.page_number))
    totals = Counter(record.extraction_status for record in records)
    audit = {
        "schema_version": "j6-extraction-v1",
        "input_manifest_sha256": manifest_hash,
        "documents_total": len(documents),
        "documents_processed": len([item for item in document_results if not item.get("error")]),
        "pages_total": len(records),
        "pages_ok": totals["ok"],
        "pages_empty": totals["empty"],
        "pages_low_text": totals["low_text"],
        "pages_error": totals["extraction_error"],
        "total_raw_chars": sum(record.raw_char_count for record in records),
        "total_clean_chars": sum(record.clean_char_count for record in records),
        "total_words": sum(record.word_count for record in records),
        "total_removed_chars": sum(
            record.raw_char_count - record.clean_char_count for record in records
        ),
        "document_results": document_results,
    }
    return records, audit


def write_extraction_outputs(repository_root: Path) -> tuple[Path, Path]:
    records, audit = extract_corpus(repository_root)
    output_dir = repository_root / "backend/data/rag/processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_path = output_dir / "pages_v1.jsonl"
    audit_path = output_dir / "extraction_v1_audit.json"
    with pages_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record.model_dump(), ensure_ascii=False, sort_keys=True) + "\n")
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return pages_path, audit_path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    pages_path, audit_path = write_extraction_outputs(root)
    print(f"pages={pages_path}")
    print(f"audit={audit_path}")
