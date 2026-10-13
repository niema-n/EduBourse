"""Deterministic page-local chunking for the frozen J6 corpus."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.rag.domain_policy import CorpusDocumentManifest
from app.rag.text_extraction import ExtractedPageRecord

TARGET_CHARS = 900
MAX_CHARS = 1200
MIN_CHARS = 250
MAX_OVERLAP_CHARS = 120
HEADING_LOOKAHEAD_PAGES = 3
BOILERPLATE_MIN_PAGES = 3
BOILERPLATE_MIN_RATIO = 0.30


class ChunkRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    language: str = "fr"
    categories: list[str] = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    page_numbers: list[int] = Field(min_length=1)
    section_heading: str | None = None
    section_heading_page: int | None = Field(default=None, ge=1)
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    text_sha256: str = Field(min_length=64, max_length=64)
    char_count: int = Field(ge=1)
    word_count: int = Field(ge=1)
    document_hash: str = Field(min_length=64, max_length=64)
    source_page_text_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("text_sha256", "document_hash", "source_page_text_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("hash must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_citation_and_text(self) -> ChunkRecord:
        if self.page_start != self.page_end or self.page_numbers != [self.page_start]:
            raise ValueError("J6-04 chunks must remain page-local")
        if self.char_count != len(self.text) or not self.text.strip():
            raise ValueError("chunk text metrics are inconsistent")
        if self.section_heading is None and self.section_heading_page is not None:
            raise ValueError("section_heading_page requires section_heading")
        return self


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _norm_line(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip().casefold()


def _edge_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return list(dict.fromkeys(lines[:2] + lines[-2:]))


def _boilerplate_candidates(pages: list[ExtractedPageRecord]) -> set[str]:
    by_document: dict[str, list[ExtractedPageRecord]] = defaultdict(list)
    for page in pages:
        if page.extraction_status in {"ok", "low_text"} and page.text.strip():
            by_document[page.source_id].append(page)
    candidates: set[str] = set()
    for document_pages in by_document.values():
        substantive = len([page for page in document_pages if page.extraction_status == "ok"])
        if not substantive:
            continue
        occurrences = Counter(
            _norm_line(line)
            for page in document_pages
            if page.extraction_status == "ok"
            for line in _edge_lines(page.text)
        )
        candidates.update(
            line
            for line, count in occurrences.items()
            if count >= BOILERPLATE_MIN_PAGES and count / substantive >= BOILERPLATE_MIN_RATIO
        )
    return candidates


def _remove_boilerplate(text: str, candidates: set[str]) -> tuple[str, int, int]:
    removed_occurrences = 0
    removed_chars = 0
    lines: list[str] = []
    for line in text.splitlines():
        if _norm_line(line) in candidates and line.strip():
            removed_occurrences += 1
            removed_chars += len(line)
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip(), removed_occurrences, removed_chars


def _word_prefix(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    prefix = text[:limit].rsplit(" ", 1)[0].rstrip()
    return prefix or text[:limit]


def _split_long_unit(unit: str) -> list[str]:
    if len(unit) <= MAX_CHARS:
        return [unit]
    sentences = re.split(r"(?<=[.!?;:])\s+", unit)
    result: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence) > MAX_CHARS:
            words = sentence.split()
            while words:
                part_words: list[str] = []
                while words and len(" ".join(part_words + [words[0]])) <= MAX_CHARS:
                    part_words.append(words.pop(0))
                result.append(" ".join(part_words))
            continue
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > MAX_CHARS:
            result.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        result.append(current)
    return result


def _base_chunks(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    units = [unit for paragraph in paragraphs for unit in _split_long_unit(paragraph)]
    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if current and len(candidate) > MAX_CHARS:
            chunks.append(current)
            current = unit
        else:
            current = candidate
            if len(current) >= TARGET_CHARS:
                chunks.append(current)
                current = ""
    if current:
        if chunks and len(current) < MIN_CHARS and len(chunks[-1]) + 2 + len(current) <= MAX_CHARS:
            chunks[-1] = f"{chunks[-1]}\n\n{current}"
        else:
            chunks.append(current)
    return chunks


def _overlap_tail(text: str) -> str:
    tail = text[-MAX_OVERLAP_CHARS:]
    return tail[tail.find(" ") + 1 :] if " " in tail else tail


def _heading_map(pages: list[ExtractedPageRecord]) -> dict[tuple[str, int], tuple[str, int]]:
    by_source: dict[str, list[ExtractedPageRecord]] = defaultdict(list)
    for page in pages:
        by_source[page.source_id].append(page)
    result: dict[tuple[str, int], tuple[str, int]] = {}
    for source_id, source_pages in by_source.items():
        ordered = sorted(source_pages, key=lambda page: page.page_number)
        for index, page in enumerate(ordered):
            if page.extraction_status != "low_text" or not page.text.strip():
                continue
            for next_page in ordered[index + 1 : index + 1 + HEADING_LOOKAHEAD_PAGES]:
                if next_page.extraction_status == "extraction_error":
                    break
                if next_page.extraction_status == "empty":
                    continue
                if next_page.extraction_status == "ok" and len(page.text.strip()) <= 180:
                    result[(source_id, next_page.page_number)] = (
                        page.text.strip(),
                        page.page_number,
                    )
                break
    return result


def chunk_pages(pages: list[ExtractedPageRecord]) -> tuple[list[ChunkRecord], dict[str, Any]]:
    if len({(page.source_id, page.page_number) for page in pages}) != len(pages):
        raise ValueError("duplicate source/page records")
    candidates = _boilerplate_candidates(pages)
    headings = _heading_map(pages)
    chunks: list[ChunkRecord] = []
    document_results: dict[str, dict[str, Any]] = {}
    for source_id in sorted({page.source_id for page in pages}):
        source_pages = sorted(
            [page for page in pages if page.source_id == source_id],
            key=lambda page: page.page_number,
        )
        result: dict[str, Any] = {
            "source_id": source_id,
            "pages_total": len(source_pages),
            "pages_chunked": 0,
            "empty_pages": 0,
            "section_heading_pages": [],
            "chunks": 0,
            "input_clean_chars": sum(page.clean_char_count for page in source_pages),
            "boilerplate_chars_removed": 0,
            "chunk_chars": 0,
            "min_chunk_chars": 0,
            "max_chunk_chars": 0,
            "warnings": [],
        }
        index = 0
        for page in source_pages:
            if page.extraction_status == "empty":
                result["empty_pages"] += 1
                continue
            if page.extraction_status == "extraction_error":
                result["warnings"].append(f"page_{page.page_number}:extraction_error")
                continue
            text, removed_count, removed_chars = _remove_boilerplate(page.text, candidates)
            result["boilerplate_chars_removed"] += removed_chars
            if not text:
                result["warnings"].append(f"page_{page.page_number}:empty_after_filter")
                continue
            if page.extraction_status == "low_text":
                continue
            bases = _base_chunks(text)
            heading, heading_page = headings.get((source_id, page.page_number), (None, None))
            if heading:
                result["section_heading_pages"].append(heading_page)
            result["pages_chunked"] += 1
            for base_index, base in enumerate(bases):
                chunk_text = base
                if base_index and len(bases) > 1:
                    overlap = _overlap_tail(bases[base_index - 1])
                    chunk_text = f"{overlap}\n{base}"
                    if len(chunk_text) > MAX_CHARS:
                        chunk_text = (
                            f"{overlap}\n{_word_prefix(base, MAX_CHARS - len(overlap) - 1)}"
                        )
                text_hash = _hash(chunk_text)
                chunk_id = f"{source_id}-p{page.page_number:03d}-c{index:03d}-{text_hash[:8]}"
                chunks.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        source_id=page.source_id,
                        title=page.title,
                        authority=page.authority,
                        language=page.language,
                        categories=list(page.categories),
                        page_start=page.page_number,
                        page_end=page.page_number,
                        page_numbers=[page.page_number],
                        section_heading=heading,
                        section_heading_page=heading_page,
                        chunk_index=index,
                        text=chunk_text,
                        text_sha256=text_hash,
                        char_count=len(chunk_text),
                        word_count=len(chunk_text.split()),
                        document_hash=page.document_hash,
                        source_page_text_sha256=page.text_sha256,
                    )
                )
                index += 1
                result["chunk_chars"] += len(chunk_text)
        result["chunks"] = index
        if index:
            sizes = [chunk.char_count for chunk in chunks if chunk.source_id == source_id]
            result["min_chunk_chars"] = min(sizes)
            result["max_chunk_chars"] = max(sizes)
        result["section_heading_pages"] = sorted(set(result["section_heading_pages"]))
        result["warnings"] = sorted(set(result["warnings"]))
        document_results[source_id] = result
    chunks.sort(key=lambda chunk: (chunk.source_id, chunk.chunk_index))
    total_removed = sum(item["boilerplate_chars_removed"] for item in document_results.values())
    total_chunk_chars = sum(chunk.char_count for chunk in chunks)
    pages_ok = [page for page in pages if page.extraction_status == "ok"]
    audit = {
        "schema_version": "j6-chunking-v1",
        "documents_total": len(document_results),
        "pages_total": len(pages),
        "pages_chunked": sum(item["pages_chunked"] for item in document_results.values()),
        "pages_empty_skipped": sum(item["empty_pages"] for item in document_results.values()),
        "pages_low_text_as_heading": len(
            [page for page in pages if page.extraction_status == "low_text"]
        ),
        "pages_error_skipped": len(
            [page for page in pages if page.extraction_status == "extraction_error"]
        ),
        "chunks_total": len(chunks),
        "chunks_per_document": {key: value["chunks"] for key, value in document_results.items()},
        "total_input_clean_chars": sum(page.clean_char_count for page in pages),
        "total_boilerplate_chars_removed": total_removed,
        "total_chunk_chars": total_chunk_chars,
        "unique_source_clean_chars_used": sum(page.clean_char_count for page in pages_ok)
        - total_removed,
        "overlap_chars_estimated": max(
            0,
            total_chunk_chars
            - sum(
                len(_base_chunks(_remove_boilerplate(page.text, candidates)[0])[i])
                for page in pages_ok
                for i in range(len(_base_chunks(_remove_boilerplate(page.text, candidates)[0])))
            ),
        ),
        "small_chunks_count": len([chunk for chunk in chunks if chunk.char_count < MIN_CHARS]),
        "max_chunk_chars": max((chunk.char_count for chunk in chunks), default=0),
        "average_chunk_chars": round(total_chunk_chars / len(chunks), 2) if chunks else 0,
        "boilerplate_lines_detected": len(candidates),
        "boilerplate_candidates": sorted(candidates),
        "boilerplate_occurrences_removed": sum(
            _remove_boilerplate(page.text, candidates)[1] for page in pages
        ),
        "section_headings_propagated": sum(
            len(item["section_heading_pages"]) for item in document_results.values()
        ),
        "chunk_id_uniqueness": len({chunk.chunk_id for chunk in chunks}) == len(chunks),
        "document_results": [document_results[key] for key in sorted(document_results)],
    }
    return chunks, audit


def _load_inputs(
    repository_root: Path,
) -> tuple[list[ExtractedPageRecord], list[CorpusDocumentManifest], str, str]:
    manifest_path = repository_root / "backend/data/rag/manifests/corpus_v1.json"
    pages_path = repository_root / "backend/data/rag/processed/pages_v1.jsonl"
    audit_path = repository_root / "backend/data/rag/processed/extraction_v1_audit.json"
    manifest_raw = manifest_path.read_bytes()
    pages_raw = pages_path.read_bytes()
    manifest_data = json.loads(manifest_raw.decode("utf-8"))
    manifest = [CorpusDocumentManifest(**item) for item in manifest_data["documents"]]
    pages = [ExtractedPageRecord.model_validate_json(line) for line in pages_raw.splitlines()]
    extraction_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected_ids = {item.source_id for item in manifest}
    if {page.source_id for page in pages} != expected_ids:
        raise ValueError("page source IDs do not match frozen manifest")
    identities = {item.source_id: item for item in manifest}
    for page in pages:
        source = identities[page.source_id]
        if (
            page.title != source.title
            or page.authority != source.authority
            or page.categories != source.category
            or page.document_hash != source.document_hash
        ):
            raise ValueError("page identity differs from frozen manifest")
    return (
        pages,
        manifest,
        hashlib.sha256(pages_raw).hexdigest(),
        extraction_audit["input_manifest_sha256"],
    )


def write_chunk_outputs(repository_root: Path) -> tuple[Path, Path]:
    pages, _, pages_hash, manifest_hash = _load_inputs(repository_root)
    chunks, audit = chunk_pages(pages)
    audit["input_pages_sha256"] = pages_hash
    audit["input_manifest_sha256"] = manifest_hash
    output_dir = repository_root / "backend/data/rag/processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = output_dir / "chunks_v1.jsonl"
    audit_path = output_dir / "chunking_v1_audit.json"
    with chunks_path.open("w", encoding="utf-8", newline="\n") as stream:
        for chunk in chunks:
            stream.write(json.dumps(chunk.model_dump(), ensure_ascii=False, sort_keys=True) + "\n")
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return chunks_path, audit_path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    chunks_path, audit_path = write_chunk_outputs(root)
    print(f"chunks={chunks_path}")
    print(f"audit={audit_path}")
