"""Isolated runtime retrieval over the frozen J6 Chroma index."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Any, Literal, Protocol

import chromadb
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rag.chroma_index import (
    COLLECTION_NAME,
    EXPECTED_DIMENSION,
    MODEL_NAME,
    MODEL_REVISION,
    resolve_bge_m3_snapshot_path,
)
from app.rag.embedding_benchmark import (
    MODEL_SPECS,
    SentenceTransformerEmbeddingProvider,
)
from app.rag.hybrid_policy import (
    HYBRID_POLICY_ID,
    RRF_K,
    fuse_rankings,
    hybrid_branches,
    rrf_scores,
)
from app.rag.query_adapter import (
    ADAPTER_MODEL,
    ADAPTER_PROMPT_SHA256,
    AdapterOutput,
    adapter_request_payload,
    contextual_adapter_payload,
    has_conversational_content,
    resolve_embedding_model_spec,
)

_STAGE_TIMINGS = threading.local()
EXPECTED_INDEXED_CHUNK_COUNT = 353

_FOLLOW_UP_RE = re.compile(
    r"\b("
    r"ses|son|sa|leur|leurs|celui|celle|ceux|celles|"
    r"ca|ça|cela|ceci|cette|cet|ce|ils|elles|eux|"
    r"respectif|respectifs|respective|respectives|"
    r"avantage|avantages|risque|risques|inconvenient|inconvénient|"
    r"fonctionne|fonctionnement|difference|différence|comparer|compare|"
    r"rendement|droits|exemples"
    r")\b",
    re.IGNORECASE,
)

_ENTITY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("actions", (r"\bactions?\b", r"\bactionnaires?\b", r"\bdividendes?\b")),
    (
        "obligations",
        (
            r"\bobligations?\b",
            r"\bcreances?\b",
            r"\bcréances?\b",
            r"\bemprunts?\b",
            r"\bcoupons?\b",
            r"\becheances?\b",
            r"\béchéances?\b",
        ),
    ),
    ("OPCVM", (r"\bopcvm\b", r"\bfonds\b", r"\bsicav\b", r"\bfcp\b")),
    (
        "introduction en bourse",
        (r"\bipo\b", r"\bintroductions?\s+en\s+bourse\b", r"\bcotation\b"),
    ),
    (
        "bourse des valeurs",
        (r"\bbourse\b", r"\bmarche\s+boursier\b", r"\bmarché\s+boursier\b"),
    ),
    (
        "marche primaire",
        (r"\bmarche\s+primaire\b", r"\bmarché\s+primaire\b"),
    ),
    (
        "marche secondaire",
        (r"\bmarche\s+secondaire\b", r"\bmarché\s+secondaire\b"),
    ),
    (
        "financement collaboratif",
        (
            r"\bfinancement\s+collaboratif\b",
            r"\bcrowdfunding\b",
            r"\bplateformes?\s+de\s+financement\b",
        ),
    ),
    (
        "operations sur titres",
        (
            r"\boperations?\s+sur\s+titres\b",
            r"\bopérations?\s+sur\s+titres\b",
            r"\bopa\b",
            r"\bopr\b",
            r"\boffres?\s+publiques?\b",
        ),
    ),
    (
        "assemblees generales",
        (
            r"\bassemblees?\s+generales?\b",
            r"\bassemblées?\s+générales?\b",
            r"\bago\b",
        ),
    ),
)

_ENTITY_PATTERN_LOOKUP: dict[str, tuple[str, ...]] = dict(_ENTITY_PATTERNS)

_SUPPORT_TERMS: tuple[tuple[str, str], ...] = (
    ("dividendes", r"\bdividendes?\b"),
    ("droits de vote", r"\bdroits?\s+de\s+vote\b|\bvote\b"),
    ("information", r"\binformation\b"),
    ("interets", r"\binterets?\b|\bintérêts?\b"),
    ("coupons", r"\bcoupons?\b"),
    ("remboursement", r"\bremboursement\b"),
    ("echeance", r"\becheance\b|\béchéance\b"),
    ("creancier", r"\bcreancier\b|\bcréancier\b"),
)


def _new_timings() -> dict[str, float]:
    return {
        "adapter_ms": 0.0,
        "adapter_calls": 0,
        "cache_hits": 0,
        "embedding_ms": 0.0,
        "embedding_calls": 0,
        "chroma_query_ms": 0.0,
        "chroma_records_ms": 0.0,
    }


def _timings() -> dict[str, float]:
    """Per-thread stage timings of the current retrieval (internal diagnostic logs only)."""
    bucket = getattr(_STAGE_TIMINGS, "values", None)
    if bucket is None:
        bucket = _new_timings()
        _STAGE_TIMINGS.values = bucket
    return bucket


def last_retrieval_timings() -> dict[str, float]:
    return dict(_timings())


INDEX_MANIFEST_SHA256 = "2585d7cb1b99632867e25d28948e78476e2fc00df7f13f402dd891bded25bfde"
SERVICE_VERSION = 1
DEFAULT_TOP_K = 5
MAX_TOP_K = 10
SUPPORTED_LANGUAGES = Literal["fr", "en", "ar", "ary"]
SUPPORTED_SCRIPTS = Literal["latin", "arabic"]


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    original_query: str = Field(min_length=1)
    language: SUPPORTED_LANGUAGES
    script: SUPPORTED_SCRIPTS
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)
    # Untrusted, bounded memory envelope. It may only shape the retrieval query;
    # evidence always comes from the indexed corpus.
    conversation_context: str | None = Field(default=None, max_length=8000)

    @model_validator(mode="after")
    def validate_language_script(self) -> RetrievalRequest:
        expected = {"fr": "latin", "en": "latin", "ar": "arabic"}
        if self.language in expected and self.script != expected[self.language]:
            raise ValueError("unsupported language/script combination")
        return self


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    chunk_id: str
    source_id: str
    title: str
    page: int
    page_start: int
    page_end: int
    heading: str | None = None
    text: str
    rank: int = Field(ge=1)
    retrieval_score: float
    score_type: Literal["cosine_distance", "rrf"]


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    original_query: str
    language: SUPPORTED_LANGUAGES
    script: SUPPORTED_SCRIPTS
    policy_id: Literal["H1_LANGUAGE_ROUTED_V1"]
    branches_used: list[str]
    adapted_query_fr: str | None = None
    adapted_query_ary_arabic: str | None = None
    chunks: list[RetrievedChunk]
    retrieval_status: Literal["ok", "provider_error", "configuration_error"]
    # Set only when a follow-up was resolved against the conversation context.
    retrieval_query: str | None = None


class RetrievalQueryAdapter(Protocol):
    model: str

    def generate(self, payload: dict[str, str]) -> AdapterOutput: ...


class RetrievalServiceError(RuntimeError):
    """Raised when the frozen local retrieval configuration is invalid."""


class RetrievalConfigurationError(RetrievalServiceError):
    """Raised for permanent local or adapter configuration failures."""


class RetrievalProviderError(RetrievalServiceError):
    """Raised for adapter execution or provider response failures."""


def retrieval_index_path(root: Path) -> Path:
    """Return the fixed on-disk location of the frozen J6 index."""
    return root / "backend/data/rag/indexes/bge_m3_v1"


def inspect_persisted_index(root: Path) -> int:
    """Read the J6 index cardinality without loading BGE-M3 or mutating Chroma."""
    client = chromadb.PersistentClient(path=str(retrieval_index_path(root)))
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=None)
    count = int(collection.count())
    if count != EXPECTED_INDEXED_CHUNK_COUNT:
        raise RetrievalConfigurationError("J6 collection cardinality mismatch")
    return count


class RetrievalService:
    """Runtime J6 retrieval without API, graph, voice, or answer generation."""

    def __init__(
        self,
        root: Path,
        *,
        embedding_provider: Any | None = None,
        query_adapter: RetrievalQueryAdapter | None = None,
        query_cache_size: int = 128,
    ) -> None:
        self.root = root
        self.query_adapter = query_adapter
        self.client = chromadb.PersistentClient(path=str(self.index_path))
        self.collection = self.client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=None,
        )
        self._validate_collection()
        self.embedding_provider = embedding_provider or self._load_embedding_provider()
        if self.embedding_provider.dimension != EXPECTED_DIMENSION:
            raise RetrievalConfigurationError("BGE embedding dimension mismatch")
        if str(self.embedding_provider.revision) != MODEL_REVISION:
            raise RetrievalConfigurationError("BGE embedding revision mismatch")
        self._chunk_ids = self.collection.get(limit=EXPECTED_INDEXED_CHUNK_COUNT, include=[])["ids"]
        if (
            len(self._chunk_ids) != EXPECTED_INDEXED_CHUNK_COUNT
            or len(set(self._chunk_ids)) != EXPECTED_INDEXED_CHUNK_COUNT
        ):
            raise RetrievalConfigurationError("J6 collection IDs are invalid")
        self._chunk_id_to_index = {
            chunk_id: index for index, chunk_id in enumerate(self._chunk_ids)
        }
        self._query_cache_size = max(0, query_cache_size)
        self._query_cache: OrderedDict[tuple[str, int], tuple[list[str], list[float]]] = (
            OrderedDict()
        )
        self._query_cache_lock = threading.Lock()

    @property
    def index_path(self) -> Path:
        return retrieval_index_path(self.root)

    def _load_embedding_provider(self) -> Any:
        snapshot = resolve_bge_m3_snapshot_path()
        spec = resolve_embedding_model_spec(MODEL_SPECS, MODEL_NAME)
        return SentenceTransformerEmbeddingProvider(
            spec,
            model_ref=snapshot,
            revision=MODEL_REVISION,
            model_kwargs={"local_files_only": True},
        )

    def _validate_collection(self) -> None:
        if chromadb.__version__ != "1.5.9":
            raise RetrievalConfigurationError("unsupported Chroma version")
        if self.collection.count() != EXPECTED_INDEXED_CHUNK_COUNT:
            raise RetrievalConfigurationError("J6 collection cardinality mismatch")
        configuration = getattr(self.collection, "configuration", {}) or {}
        if configuration.get("embedding_function") is not None:
            raise RetrievalConfigurationError("Chroma embedding function must be None")
        if configuration.get("hnsw", {}).get("space") != "cosine":
            raise RetrievalConfigurationError("J6 collection must use cosine distance")
        if (self.collection.metadata or {}).get("hnsw:space") != "cosine":
            raise RetrievalConfigurationError("J6 collection metadata must use cosine distance")
        sample = self.collection.get(limit=1, include=["embeddings"])
        embeddings = sample.get("embeddings")
        if embeddings is None or len(embeddings) != 1 or len(embeddings[0]) != EXPECTED_DIMENSION:
            raise RetrievalConfigurationError("J6 stored embedding dimension mismatch")

    def _adapt(self, request: RetrievalRequest) -> tuple[str, str | None]:
        if self.query_adapter is None:
            raise RetrievalConfigurationError("query adapter is required for this H1 branch")
        if getattr(self.query_adapter, "model", ADAPTER_MODEL) != ADAPTER_MODEL:
            raise RetrievalConfigurationError("query adapter model mismatch")
        started = time.perf_counter()
        try:
            output = self.query_adapter.generate(
                adapter_request_payload(request_to_gold_case(request))
            )
        except Exception as exc:
            raise RetrievalProviderError("query adapter execution failed") from exc
        finally:
            _timings()["adapter_ms"] += (time.perf_counter() - started) * 1000
            _timings()["adapter_calls"] += 1
        return self._validated_adapter_output(request, output)

    def _uses_contextual_adapter(self, request: RetrievalRequest) -> bool:
        """Follow-ups are resolved only when context exists and the adapter supports it."""
        return (
            has_conversational_content(request.conversation_context)
            and self.query_adapter is not None
            and getattr(self.query_adapter, "model", ADAPTER_MODEL) == ADAPTER_MODEL
            and callable(getattr(self.query_adapter, "generate_contextual", None))
        )

    def _adapt_contextual(self, request: RetrievalRequest) -> tuple[str, str | None]:
        started = time.perf_counter()
        try:
            output = self.query_adapter.generate_contextual(
                contextual_adapter_payload(
                    request.original_query,
                    request.language,
                    request.script,
                    request.conversation_context or "",
                )
            )
        except Exception as exc:
            raise RetrievalProviderError("contextual query adapter execution failed") from exc
        finally:
            _timings()["adapter_ms"] += (time.perf_counter() - started) * 1000
            _timings()["adapter_calls"] += 1
        return self._validated_adapter_output(request, output)

    @staticmethod
    def _fold_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "")
        ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", ascii_text.casefold()).strip()

    @classmethod
    def _conversation_text(cls, context: str | None) -> str:
        if not context:
            return ""
        try:
            payload = json.loads(context)
        except (TypeError, ValueError):
            return ""
        if not isinstance(payload, dict):
            return ""
        parts: list[str] = []
        for key in ("recent", "relevant_old"):
            turns = payload.get(key)
            if not isinstance(turns, list):
                continue
            for turn in turns:
                if isinstance(turn, dict):
                    content = turn.get("content")
                    if isinstance(content, str):
                        parts.append(content)
        return " ".join(parts)

    @classmethod
    def _contextual_entities(cls, context: str | None) -> list[str]:
        text = cls._fold_text(cls._conversation_text(context))
        if not text:
            return []
        matches: list[tuple[int, str]] = []
        for label, patterns in _ENTITY_PATTERNS:
            positions = [
                match.start()
                for pattern in patterns
                for match in re.finditer(cls._fold_text(pattern), text)
            ]
            if positions:
                matches.append((min(positions), label))
        return [label for _, label in sorted(matches)]

    @classmethod
    def _contextual_support_terms(cls, context: str | None) -> list[str]:
        text = cls._fold_text(cls._conversation_text(context))
        if not text:
            return []
        terms = []
        for label, pattern in _SUPPORT_TERMS:
            if re.search(cls._fold_text(pattern), text):
                terms.append(label)
        return terms

    @classmethod
    def _is_follow_up_query(cls, query: str) -> bool:
        text = cls._fold_text(query)
        return bool(_FOLLOW_UP_RE.search(text) or re.match(r"^(et|aussi|alors|puis)\b", text))

    @classmethod
    def _entity_already_present(cls, entity: str, folded_query: str) -> bool:
        """True when the adapter's own wording already names this entity.

        Reuses the same detection patterns as `_contextual_entities` (plural,
        singular and near-synonym forms) instead of a raw label substring
        match, which would miss e.g. "action" resolving the label "actions".
        """
        patterns = _ENTITY_PATTERN_LOOKUP.get(entity, ())
        if any(re.search(cls._fold_text(pattern), folded_query) for pattern in patterns):
            return True
        return cls._fold_text(entity) in folded_query

    @classmethod
    def _reinforce_contextual_query(
        cls, request: RetrievalRequest, adapted_fr: str
    ) -> str:
        """Make elliptical follow-up searches self-contained when the adapter is vague.

        The conversation text is untrusted and only contributes topic words for retrieval.
        Answer evidence still comes exclusively from retrieved corpus chunks.
        """
        if not cls._is_follow_up_query(request.original_query):
            return adapted_fr
        entities = cls._contextual_entities(request.conversation_context)
        if not entities:
            return adapted_fr
        folded_query = cls._fold_text(adapted_fr)
        missing_entities = [
            entity for entity in entities if not cls._entity_already_present(entity, folded_query)
        ]
        # Support vocabulary (dividendes, coupons, echeance, ...) is the part of the
        # prior answer that actually distinguishes "avantages"/"risques" between
        # topics; it is worth adding even when the adapter already named every
        # topic, since a topic name alone rarely matches the source wording.
        support_terms = [
            term
            for term in cls._contextual_support_terms(request.conversation_context)
            if cls._fold_text(term) not in folded_query
        ][:6]
        if not missing_entities and not support_terms:
            return adapted_fr
        suffix_parts = []
        if missing_entities:
            suffix_parts.append("sur " + " et ".join(missing_entities))
        if support_terms:
            suffix_parts.append(" ".join(support_terms))
        suffix = " " + " ".join(suffix_parts)
        return re.sub(r"\s+", " ", f"{adapted_fr.strip()} {suffix}").strip()

    @staticmethod
    def _validated_adapter_output(
        request: RetrievalRequest, output: object
    ) -> tuple[str, str | None]:
        try:
            if not isinstance(output, AdapterOutput):
                output = AdapterOutput.model_validate(output)
            if request.language == "ary" and request.script == "latin":
                if output.retrieval_query_ary_arabic is None:
                    raise ValueError("Ary-Latin adapter output is incomplete")
            elif output.retrieval_query_ary_arabic is not None:
                raise ValueError("unexpected Ary-Arabic adapter output")
            return output.retrieval_query_fr, output.retrieval_query_ary_arabic
        except Exception as exc:
            raise RetrievalProviderError("query adapter response is invalid") from exc

    def _query(self, query: str, n_results: int) -> tuple[list[str], list[float]]:
        cache_key = (query, n_results)
        if self._query_cache_size > 0:
            with self._query_cache_lock:
                cached = self._query_cache.get(cache_key)
                if cached is not None:
                    self._query_cache.move_to_end(cache_key)
                    _timings()["cache_hits"] += 1
                    ids, distances = cached
                    return list(ids), list(distances)
        started = time.perf_counter()
        vector = self.embedding_provider.embed_queries([query])[0]
        embedded = time.perf_counter()
        response = self.collection.query(
            query_embeddings=[vector.tolist()],
            n_results=n_results,
            include=["distances"],
        )
        _timings()["embedding_ms"] += (embedded - started) * 1000
        _timings()["chroma_query_ms"] += (time.perf_counter() - embedded) * 1000
        _timings()["embedding_calls"] += 1
        ids = list(response["ids"][0])
        distances = list(response["distances"][0])
        if self._query_cache_size > 0:
            with self._query_cache_lock:
                self._query_cache[cache_key] = (ids, distances)
                self._query_cache.move_to_end(cache_key)
                while len(self._query_cache) > self._query_cache_size:
                    self._query_cache.popitem(last=False)
        return ids, distances

    def _records(
        self, ids: list[str], scores: dict[str, float], score_type: str
    ) -> list[RetrievedChunk]:
        started = time.perf_counter()
        response = self.collection.get(ids=ids, include=["documents", "metadatas"])
        _timings()["chroma_records_ms"] += (time.perf_counter() - started) * 1000
        by_id = {
            chunk_id: (document, metadata)
            for chunk_id, document, metadata in zip(
                response["ids"], response["documents"], response["metadatas"], strict=True
            )
        }
        result = []
        for rank, chunk_id in enumerate(ids, start=1):
            document, metadata = by_id[chunk_id]
            result.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    source_id=metadata["source_id"],
                    title=metadata["title"],
                    page=metadata["page"],
                    page_start=metadata["page_start"],
                    page_end=metadata["page_end"],
                    heading=metadata.get("heading"),
                    text=document,
                    rank=rank,
                    retrieval_score=float(scores[chunk_id]),
                    score_type=score_type,
                )
            )
        return result

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        _STAGE_TIMINGS.values = _new_timings()
        return self._retrieve(request)

    def _retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        record = {
            "original_query": request.original_query,
            "retrieval_query_fr": request.original_query,
            "retrieval_query_ary_arabic": None,
        }
        adapted_fr = None
        adapted_ary = None
        retrieval_query = None
        needs_adapter = request.language in {"en", "ar"} or request.language == "ary"
        contextual = self._uses_contextual_adapter(request)
        if contextual:
            # One adapter call replaces the single-turn one for en/ar/ary; for fr it
            # is the only adapter call and happens on follow-up turns only.
            try:
                adapted_fr, adapted_ary = self._adapt_contextual(request)
            except RetrievalProviderError:
                if needs_adapter:
                    return self._failure_result(request, "provider_error")
                # French already works without an adapter: degrade to the raw query.
                contextual = False
        if contextual:
            retrieval_query = adapted_fr
            record["retrieval_query_fr"] = adapted_fr
            record["retrieval_query_ary_arabic"] = adapted_ary
            if request.language == "fr":
                adapted_fr = self._reinforce_contextual_query(request, adapted_fr)
                retrieval_query = adapted_fr
                record["retrieval_query_fr"] = adapted_fr
        elif needs_adapter:
            try:
                adapted_fr, adapted_ary = self._adapt(request)
            except RetrievalConfigurationError:
                return self._failure_result(request, "configuration_error")
            except RetrievalProviderError:
                return self._failure_result(request, "provider_error")
            except RetrievalServiceError:
                return self._failure_result(request, "configuration_error")
            record["retrieval_query_fr"] = adapted_fr
            record["retrieval_query_ary_arabic"] = adapted_ary
        if contextual and request.language == "fr":
            # The frozen H1 policy searches the raw French text; a resolved
            # follow-up searches its self-contained form instead.
            branches = [("contextual_french", adapted_fr)]
        else:
            branches = hybrid_branches(request.language, request.script, record)
        branch_ids: list[list[str]] = []
        branch_distances: dict[str, float] = {}
        for _name, query in branches:
            ids, distances = self._query(query, 353 if len(branches) > 1 else request.top_k)
            branch_ids.append(ids)
            if len(branches) == 1:
                branch_distances = dict(zip(ids, distances, strict=True))
        if len(branches) == 1:
            ids = branch_ids[0][: request.top_k]
            return RetrievalResult(
                original_query=request.original_query,
                language=request.language,
                script=request.script,
                policy_id=HYBRID_POLICY_ID,
                branches_used=[name for name, _ in branches],
                adapted_query_fr=adapted_fr,
                adapted_query_ary_arabic=adapted_ary,
                chunks=self._records(ids, branch_distances, "cosine_distance"),
                retrieval_status="ok",
                retrieval_query=retrieval_query,
            )
        index_rankings = [
            [self._chunk_id_to_index[chunk_id] for chunk_id in ids] for ids in branch_ids
        ]
        index_chunks = [type("Chunk", (), {"chunk_id": value})() for value in self._chunk_ids]
        fused_indexes = fuse_rankings(index_rankings, index_chunks, RRF_K)
        ids = [self._chunk_ids[index] for index in fused_indexes[: request.top_k]]
        scores_by_index = rrf_scores(index_rankings, RRF_K)
        scores = {
            self._chunk_ids[index]: scores_by_index[index]
            for index in fused_indexes[: request.top_k]
        }
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id=HYBRID_POLICY_ID,
            branches_used=[name for name, _ in branches],
            adapted_query_fr=adapted_fr,
            adapted_query_ary_arabic=adapted_ary,
            chunks=self._records(ids, scores, "rrf"),
            retrieval_status="ok",
            retrieval_query=retrieval_query,
        )

    @staticmethod
    def _failure_result(
        request: RetrievalRequest, status: Literal["provider_error", "configuration_error"]
    ) -> RetrievalResult:
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id=HYBRID_POLICY_ID,
            branches_used=[],
            chunks=[],
            retrieval_status=status,
        )


def request_to_gold_case(request: RetrievalRequest) -> Any:
    """Build the adapter's minimal typed input without exposing gold metadata."""
    return type(
        "RuntimeAdapterCase",
        (),
        {
            "id": "runtime",
            "query": request.original_query,
            "language": request.language,
            "script": request.script,
        },
    )()


def service_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "backend/data/rag/manifests/chroma_index_v1.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != INDEX_MANIFEST_SHA256:
        raise RetrievalServiceError("J6 index manifest hash mismatch")
    return {
        "schema_version": "j6-retrieval-service-v1",
        "service_version": SERVICE_VERSION,
        "retrieval_policy": HYBRID_POLICY_ID,
        "rrf_k": RRF_K,
        "index_path": "backend/data/rag/indexes/bge_m3_v1",
        "collection_name": COLLECTION_NAME,
        "index_manifest_sha256": INDEX_MANIFEST_SHA256,
        "required_chromadb_version": "1.5.9",
        "embedding_function_none_required": True,
        "embedding_model": MODEL_NAME,
        "embedding_revision": MODEL_REVISION,
        "embedding_dimension": EXPECTED_DIMENSION,
        "distance_metric": "cosine",
        "collection_count": 353,
        "default_top_k": DEFAULT_TOP_K,
        "max_top_k": MAX_TOP_K,
        "ary_latin_full_corpus_rrf": True,
        "provider_required_languages": ["en", "ar", "ary"],
        "query_adapter_model": ADAPTER_MODEL,
        "query_adapter_prompt_sha256": ADAPTER_PROMPT_SHA256,
        "retrieval_statuses": ["ok", "provider_error", "configuration_error"],
        "provider_error_retryable": True,
        "configuration_error_retryable": False,
        "confirmatory_quality_gate": False,
        "retrieval_policy_status": "ACCEPTED_WITH_DOCUMENTED_CONFIRMATORY_LIMITATIONS",
        "known_limitations": [
            "Ary-Latin RRF dilution.",
            "The brochure placement source has only three content chunks and "
            "creates cross-language competition.",
        ],
        "no_more_retrieval_policy_tuning": True,
        "answer_generation": False,
        "production_integration": False,
        "next_step": "J6_08_GROUNDED_GENERATION",
    }
