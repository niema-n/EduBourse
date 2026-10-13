"""Deterministic post-search validation of web-grounding sources.

The model prompt only *prefers* official sources. This policy decides: a
web-grounded answer is kept only when every grounding source resolves to an
approved financial host. One unapproved or unidentifiable source rejects the
whole answer, because the final text cannot be proven to come only from
approved sources.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

from app.rag.domain_policy import APPROVED_AUTHORITY_PRIORITY, APPROVED_SOURCE_HOSTS

_HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
# Grounding URIs point to Google's redirect service, never to the publisher.
_REDIRECT_HOSTS = ("vertexaisearch.cloud.google.com", "google.com")


def _normalize_host(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    host = value.strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host if _HOST_RE.match(host) else None


def project_approved_hosts() -> tuple[str, ...]:
    """Official hosts of the project's approved authorities, in priority order."""
    hosts: list[str] = []
    for authority in APPROVED_AUTHORITY_PRIORITY:
        hosts.extend(APPROVED_SOURCE_HOSTS.get(authority, ()))
    return tuple(hosts)


def parse_extra_domains(raw: str | None) -> tuple[str, ...]:
    """Explicitly approved issuer/financial domains (comma-separated); invalid entries ignored."""
    if not raw:
        return ()
    domains = (_normalize_host(part) for part in raw.split(","))
    return tuple(domain for domain in domains if domain)


def approved_domains(extra: Iterable[str] = ()) -> tuple[str, ...]:
    ordered: list[str] = []
    for host in (*project_approved_hosts(), *extra):
        normalized = _normalize_host(host)
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return tuple(ordered)


def source_host(source: Mapping[str, object]) -> str | None:
    """Publisher host of one grounding chunk, or None when it cannot be identified."""
    for key in ("domain", "title"):
        host = _normalize_host(source.get(key))  # type: ignore[arg-type]
        if host:
            return host
    uri = source.get("uri")
    if isinstance(uri, str) and uri.startswith("https://"):
        host = _normalize_host(urlsplit(uri).hostname)
        if host and not any(host == r or host.endswith("." + r) for r in _REDIRECT_HOSTS):
            return host
    return None


def is_approved_host(host: str | None, domains: Iterable[str]) -> bool:
    if not host:
        return False
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def all_sources_approved(sources: Iterable[Mapping[str, object]], domains: Iterable[str]) -> bool:
    """True only for a non-empty source list whose every entry is an approved host."""
    domain_list = tuple(domains)
    items = list(sources)
    return bool(items) and all(
        is_approved_host(source_host(source), domain_list) for source in items
    )
