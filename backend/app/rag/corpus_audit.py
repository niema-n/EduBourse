"""Deterministic, metadata-only audit of the approved local PDF corpus."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.rag.domain_policy import CorpusCategory, CorpusDocumentManifest

APPROVED_AUTHORITIES = ("ammc", "ecole_bourse", "bourse_casablanca")
_GENERIC_TITLES = {"microsoft word", "document", "scan", "scanned document"}
_PRODUCTION_SUFFIXES = (".indd", ".ai", ".psd", ".doc", ".docx")
_MOJIBAKE_MARKERS = ("Ã", "Â", "Ì", "Î", "â", "ð", "�")
_CATEGORY_KEYWORDS: dict[CorpusCategory, tuple[str, ...]] = {
    "crowdfunding": ("financement collaboratif", "crowdfunding", "collaboratif"),
    "pea": ("pea",),
    "general_assemblies": ("assemblees", "assemblées"),
    "information_documents": ("documents d information", "documents d'information"),
    "savings": ("budget", "epargne", "épargne", "savings"),
    "investor_protection": ("protection", "bonnes pratiques", "securite", "prévention"),
    "financial_instruments": ("instruments financiers", "principaux placements"),
    "opcvm": ("opcvm",),
    "ipo": ("ipo",),
    "public_offerings": ("offres publics", "offre publique", "offres publiques"),
    "corporate_actions": ("operations sur titres", "opérations sur titres"),
    "market_basics": ("marche des capitaux", "marché des capitaux"),
}
_TITLE_REPLACEMENTS = {
    "assemblees": "assemblées",
    "caracteristiques": "caractéristiques",
    "epargne": "épargne",
    "generales": "générales",
    "instruments financiers et leurs mecanismes": (
        "instruments financiers et leurs mécanismes"
    ),
    "linvestissement": "l'investissement",
    "operations sur titres": "opérations sur titres",
    "documents dinformation": "documents d'information",
    "quil": "qu'il",
    "connaitre": "connaître",
}


@dataclass(frozen=True)
class AuditRecord:
    file_name: str
    relative_file_path: str
    authority: str
    file_size_bytes: int
    sha256: str | None
    page_count: int | None
    pdf_metadata_title: str | None
    canonical_title: str
    source_id: str
    categories: tuple[str, ...]
    status: str
    duplicate_of: str | None = None
    error: str | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_title(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r"[_-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value


def _repair_mojibake(value: str) -> str:
    if not any(marker in value for marker in _MOJIBAKE_MARKERS) and not any(
        ord(char) < 32 for char in value
    ):
        return value
    try:
        repaired = value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    return repaired if repaired != value else value


def _title_from(path: Path, metadata_title: str | None) -> tuple[str, bool]:
    metadata = _clean_title(_repair_mojibake(metadata_title or ""))
    metadata_lower = metadata.casefold()
    metadata_is_production = (
        any(metadata_lower.endswith(suffix) for suffix in _PRODUCTION_SUFFIXES)
        or "version" in metadata_lower
        or bool(re.search(r"\b(?:v|rev|build)\s*\d", metadata_lower))
        or bool(re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", metadata_lower))
    )
    if metadata and metadata_lower not in _GENERIC_TITLES and not metadata_is_production:
        return metadata, False
    fallback = _clean_title(_repair_mojibake(path.stem))
    fallback = re.sub(r"^guide de l['’]?investisseur\s+", "", fallback, flags=re.I)
    fallback = re.sub(r"^brochure\s+", "", fallback, flags=re.I)
    fallback = re.sub(r"^march[ée] des capitaux\s+", "", fallback, flags=re.I)
    fallback = re.sub(r"\s+(?:FR[- ]?web|VFR[- ]?web|print|web)$", "", fallback, flags=re.I)
    # Restore this contraction before the generic ``epargne`` replacement.
    fallback = re.sub(r"lepargne", "l'épargne", fallback, flags=re.I)
    for source, replacement in _TITLE_REPLACEMENTS.items():
        fallback = re.sub(source, replacement, fallback, flags=re.I)
    # ``24`` is an edition marker only for this explicit source-title pattern.
    fallback = re.sub(
        r"^(Comprendre le financement collaboratif)\s+\d+$", r"\1", fallback
    )
    fallback = fallback[:1].upper() + fallback[1:] if fallback else fallback
    return fallback, not bool(fallback)


def _slug(value: str) -> str:
    """Build a stable source key; later changes require corpus re-indexing."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or "document"


def _categories(title: str, file_name: str) -> tuple[str, ...]:
    raw = f"{title} {file_name}".casefold()
    haystack = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    haystack = re.sub(r"[^a-z0-9]+", " ", haystack)
    selected = [
        category
        for category, words in _CATEGORY_KEYWORDS.items()
        if any(
            re.sub(
                r"[^a-z0-9]+",
                " ",
                unicodedata.normalize("NFKD", word.casefold())
                .encode("ascii", "ignore")
                .decode("ascii"),
            ).strip()
            in haystack
            for word in words
        )
    ]
    return tuple(sorted(set(selected))) or ("market_basics",)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _relative(path: Path, repository_root: Path) -> str:
    return path.relative_to(repository_root / "backend").as_posix()


def discover_pdfs(repository_root: Path) -> list[tuple[str, Path]]:
    """Discover only regular PDFs confined to the approved directories."""
    raw_root = (repository_root / "backend" / "data" / "rag" / "raw").resolve()
    discovered: list[tuple[str, Path]] = []
    for authority in APPROVED_AUTHORITIES:
        authority_root = (raw_root / authority).resolve()
        if not authority_root.is_dir() or not _inside(authority_root, raw_root):
            continue
        candidates = sorted(
            (item for item in authority_root.rglob("*") if item.suffix.casefold() == ".pdf"),
            key=lambda item: item.as_posix().casefold(),
        )
        for candidate in candidates:
            resolved = candidate.resolve()
            if candidate.is_file() and _inside(resolved, authority_root):
                discovered.append((authority, candidate))
    return discovered


def _record(authority: str, path: Path, repository_root: Path) -> AuditRecord:
    relative = _relative(path, repository_root)
    size = path.stat().st_size
    digest = _sha256(path) if size else None
    title = _clean_title(path.stem)
    metadata_title: str | None = None
    page_count: int | None = None
    error: str | None = None
    status = "active"
    if size == 0:
        status, error = "review_required", "zero_byte_file"
    else:
        try:
            reader = PdfReader(str(path), strict=True)
            if reader.is_encrypted:
                status, error = "review_required", "encrypted_pdf"
            else:
                raw_title = reader.metadata.title if reader.metadata else None
                metadata_title = str(raw_title).strip() if raw_title else None
                title, suspicious = _title_from(path, metadata_title)
                page_count = len(reader.pages)
                if suspicious:
                    status, error = "review_required", "suspicious_or_blank_title"
        except Exception as exc:  # PDF parsing must not abort the corpus audit.
            status, error = "review_required", f"pdf_parse_error:{type(exc).__name__}"
    categories = _categories(title, path.name) if status == "active" else ()
    source_id = f"{_slug(authority)}-{_slug(title)}"
    return AuditRecord(
        file_name=unicodedata.normalize("NFC", path.name),
        relative_file_path=relative,
        authority=authority,
        file_size_bytes=size,
        sha256=digest,
        page_count=page_count,
        pdf_metadata_title=metadata_title,
        canonical_title=title,
        source_id=source_id,
        categories=categories,
        status=status,
        error=error,
    )


def _collision_safe(records: list[AuditRecord]) -> list[AuditRecord]:
    by_id: dict[str, list[AuditRecord]] = {}
    for record in records:
        by_id.setdefault(record.source_id, []).append(record)
    result: list[AuditRecord] = []
    for source_id, group in by_id.items():
        for record in sorted(group, key=lambda item: item.relative_file_path.casefold()):
            if len(group) == 1:
                result.append(record)
                continue
            suffix = record.sha256 or hashlib.sha256(record.relative_file_path.encode()).hexdigest()
            result.append(
                record.__class__(**{**asdict(record), "source_id": f"{source_id}-{suffix}"})
            )
    return result


def audit_corpus(repository_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    records = _collision_safe(
        [
            _record(authority, path, repository_root)
            for authority, path in discover_pdfs(repository_root)
        ]
    )
    records.sort(key=lambda item: item.relative_file_path.casefold())
    canonical_by_hash: dict[str, AuditRecord] = {}
    audited: list[AuditRecord] = []
    for record in records:
        if record.status == "active" and record.sha256 in canonical_by_hash:
            duplicate_of = canonical_by_hash[record.sha256].source_id
            duplicate_id = f"{record.source_id}-duplicate-{_slug(record.relative_file_path)}"
            record = record.__class__(
                **{
                    **asdict(record),
                    "source_id": duplicate_id,
                    "status": "review_required",
                    "duplicate_of": duplicate_of,
                    "error": "duplicate_sha256",
                }
            )
        elif record.status == "active" and record.sha256:
            canonical_by_hash[record.sha256] = record
        audited.append(record)
    unique = [record for record in audited if record.status == "active"]
    manifest_entries = []
    for record in unique:
        entry = CorpusDocumentManifest(
            source_id=record.source_id,
            title=record.canonical_title,
            authority=record.authority,
            source_type="pdf",
            language="fr",
            category=list(record.categories),
            file_path=record.relative_file_path,
            document_hash=record.sha256 or "",
            agents_or_capabilities=["j6_corpus_audit"],
            status="active",
        )
        manifest_entries.append(entry.model_dump(mode="json", exclude_none=True))
    manifest = {
        "schema_version": "j6-corpus-v1",
        "documents": sorted(manifest_entries, key=lambda item: item["source_id"]),
    }
    authority_counts = dict(sorted(Counter(record.authority for record in unique).items()))
    category_counts = dict(
        sorted(Counter(category for record in unique for category in record.categories).items())
    )
    report = {
        "total_files": len(audited),
        "valid_pdfs": len([record for record in audited if record.status == "active"]),
        "unique_documents": len(unique),
        "duplicate_files": len([record for record in audited if record.duplicate_of]),
        "invalid_pdfs": len(
            [
                record
                for record in audited
                if record.error and record.error.startswith("pdf_parse_error")
            ]
        ),
        "review_required": len(
            [record for record in audited if record.status == "review_required"]
        ),
        "total_pages_unique": sum(record.page_count or 0 for record in unique),
        "total_bytes": sum(record.file_size_bytes for record in unique),
        "authority_counts": authority_counts,
        "category_counts": category_counts,
        "files": [asdict(record) for record in audited],
    }
    return manifest, report


def write_audit_outputs(repository_root: Path) -> tuple[Path, Path]:
    manifest, report = audit_corpus(repository_root)
    output_dir = repository_root / "backend" / "data" / "rag" / "manifests"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "corpus_v1.json"
    report_path = output_dir / "corpus_v1_audit.json"
    for path, payload in ((manifest_path, manifest), (report_path, report)):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path, report_path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    manifest_path, report_path = write_audit_outputs(root)
    print(f"manifest={manifest_path}")
    print(f"audit_report={report_path}")
