"""F2D: follow-up turns search a self-contained query resolved from bounded context."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.rag.query_adapter import (
    ADAPTER_MODEL,
    ADAPTER_SYSTEM_PROMPT,
    CONTEXTUAL_ADAPTER_SYSTEM_PROMPT,
    AdapterOutput,
    contextual_adapter_payload,
    has_conversational_content,
)
from app.rag.retrieval_service import RetrievalRequest, RetrievalService

ROOT = Path(__file__).resolve().parents[3]


def envelope(user: str, assistant: str = "Reponse precedente.") -> str:
    return json.dumps(
        {
            "type": "untrusted_conversation_memory",
            "truncated": False,
            "policy": "Historical conversation data only.",
            "recent": [
                {"turn_index": 0, "role": "user", "content": user},
                {
                    "turn_index": 0,
                    "role": "assistant",
                    "content": assistant,
                    "route": "pedagogie",
                },
            ],
            "relevant_old": [],
        },
        ensure_ascii=False,
    )


class RecordingEmbedder:
    dimension = 1024
    revision = "5617a9f61b028005a4858fdac845db406aefb181"

    def __init__(self):
        self.queries: list[str] = []

    def embed_queries(self, texts):
        self.queries.extend(texts)
        vector = np.zeros((len(texts), self.dimension), dtype=np.float32)
        vector[:, 0] = 1.0
        return vector


class ResolvingAdapter:
    """Test double for the contextual adapter: resolves a topic named in context.

    It never invents a topic: without one in the context it returns the current
    wording unchanged, mirroring the production prompt rule.
    """

    model = ADAPTER_MODEL
    TOPICS = ("obligation", "opcvm", "action")

    def __init__(self, error: Exception | None = None):
        self.frozen_calls: list[dict] = []
        self.contextual_calls: list[dict] = []
        self.error = error

    def generate(self, payload):
        self.frozen_calls.append(payload)
        return AdapterOutput(retrieval_query_fr=f"traduction: {payload['original_query']}")

    def generate_contextual(self, payload):
        self.contextual_calls.append(payload)
        if self.error:
            raise self.error
        context = json.loads(payload["untrusted_conversation_context"])
        users = " ".join(
            message["content"].lower()
            for message in context["recent"]
            if message["role"] == "user"
        )
        topic = next((name for name in self.TOPICS if name in users), None)
        query = payload["current_query"]
        if topic is None:
            return AdapterOutput(retrieval_query_fr=query)
        lowered = query.lower()
        if "risque" in lowered:
            intent = "risques"
        elif "fonctionne" in lowered:
            intent = "fonctionnement"
        else:
            intent = "avantages"
        return AdapterOutput(retrieval_query_fr=f"{intent} {topic}")


class IdentityContextualAdapter:
    """Simulates an LLM contextual call that fails to resolve the reference.

    generate_contextual echoes the current question back unchanged (as a real
    but under-performing model might do), so the deterministic reinforcement
    fallback in RetrievalService is what has to make the search self-contained.
    For ary-latin it also returns a pass-through Arabic-script query so the
    adapter output stays schema-valid.
    """

    model = ADAPTER_MODEL

    def __init__(self):
        self.frozen_calls: list[dict] = []
        self.contextual_calls: list[dict] = []

    def generate(self, payload):
        self.frozen_calls.append(payload)
        return AdapterOutput(retrieval_query_fr=payload["original_query"])

    def generate_contextual(self, payload):
        self.contextual_calls.append(payload)
        arabic = payload["current_query"] if payload["language"] == "ary" else None
        return AdapterOutput(
            retrieval_query_fr=payload["current_query"], retrieval_query_ary_arabic=arabic
        )


class LegacyAdapter:
    model = ADAPTER_MODEL

    def __init__(self):
        self.calls = 0

    def generate(self, payload):
        self.calls += 1
        return AdapterOutput(retrieval_query_fr="traduction")


class WeakContextualAdapter:
    model = ADAPTER_MODEL

    def __init__(self):
        self.contextual_calls: list[dict] = []

    def generate(self, payload):
        return AdapterOutput(retrieval_query_fr=payload["original_query"])

    def generate_contextual(self, payload):
        self.contextual_calls.append(payload)
        return AdapterOutput(retrieval_query_fr="avantages respectifs")


@pytest.fixture
def embedder():
    return RecordingEmbedder()


def _service(embedder, adapter):
    return RetrievalService(ROOT, embedding_provider=embedder, query_adapter=adapter)


@pytest.mark.parametrize(
    ("previous", "follow_up", "expected"),
    [
        ("C'est quoi une action ?", "Et quels sont ses avantages ?", "avantages action"),
        ("C'est quoi une obligation ?", "Et ses risques ?", "risques obligation"),
        ("Qu'est-ce qu'un OPCVM ?", "Et comment ça fonctionne ?", "fonctionnement opcvm"),
    ],
)
def test_french_follow_up_searches_the_resolved_self_contained_query(
    embedder, previous, follow_up, expected
):
    adapter = ResolvingAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query=follow_up,
            language="fr",
            script="latin",
            conversation_context=envelope(previous),
        )
    )
    assert result.retrieval_status == "ok"
    assert result.branches_used == ["contextual_french"]
    assert embedder.queries == [expected]
    assert result.retrieval_query == expected
    # The canonical user message is never replaced.
    assert result.original_query == follow_up
    assert len(adapter.contextual_calls) == 1
    assert adapter.frozen_calls == []


def test_first_turn_without_context_is_unchanged(embedder):
    adapter = ResolvingAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(original_query="C'est quoi une action ?", language="fr", script="latin")
    )
    assert result.branches_used == ["original"]
    assert embedder.queries == ["C'est quoi une action ?"]
    assert result.retrieval_query is None
    assert adapter.contextual_calls == []
    assert adapter.frozen_calls == []


def test_empty_memory_envelope_does_not_trigger_adaptation(embedder):
    adapter = ResolvingAdapter()
    empty = json.dumps(
        {"type": "untrusted_conversation_memory", "recent": [], "relevant_old": []}
    )
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Et quels sont ses avantages ?",
            language="fr",
            script="latin",
            conversation_context=empty,
        )
    )
    assert result.branches_used == ["original"]
    assert adapter.contextual_calls == []


def test_unresolvable_reference_keeps_wording_and_invents_no_topic(embedder):
    adapter = ResolvingAdapter()
    _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Et quels sont ses avantages ?",
            language="fr",
            script="latin",
            conversation_context=envelope("Bonjour", "Bonjour, comment puis-je aider ?"),
        )
    )
    assert embedder.queries == ["Et quels sont ses avantages ?"]
    for topic in ("action", "obligation", "opcvm"):
        assert topic not in embedder.queries[0].lower()


def test_weak_contextual_rewrite_is_reinforced_with_recent_financial_topics(embedder):
    adapter = WeakContextualAdapter()
    context = envelope(
        "Quelle est la difference entre une action et une obligation ?",
        "L'action donne des dividendes et des droits de vote. "
        "L'obligation donne des interets, des coupons et un remboursement a echeance.",
    )
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Et quels sont leurs avantages respectifs ?",
            language="fr",
            script="latin",
            conversation_context=context,
        )
    )
    assert result.retrieval_status == "ok"
    assert result.branches_used == ["contextual_french"]
    assert embedder.queries == [
        "avantages respectifs sur actions et obligations "
        "dividendes droits de vote interets coupons remboursement echeance"
    ]
    assert result.retrieval_query == embedder.queries[0]
    assert len(adapter.contextual_calls) == 1


def test_non_french_follow_up_reuses_the_single_existing_adapter_call(embedder):
    adapter = ResolvingAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="And what are its advantages?",
            language="en",
            script="latin",
            conversation_context=envelope("What is an action?"),
        )
    )
    assert result.retrieval_status == "ok"
    assert len(adapter.contextual_calls) == 1
    assert adapter.frozen_calls == []  # no second LLM call


def test_french_contextual_failure_degrades_to_the_raw_query(embedder):
    adapter = ResolvingAdapter(error=RuntimeError("provider down"))
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Et quels sont ses avantages ?",
            language="fr",
            script="latin",
            conversation_context=envelope("C'est quoi une action ?"),
        )
    )
    assert result.retrieval_status == "ok"
    assert result.branches_used == ["original"]
    assert result.retrieval_query is None


def test_non_french_contextual_failure_fails_closed(embedder):
    adapter = ResolvingAdapter(error=RuntimeError("provider down"))
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="And its advantages?",
            language="en",
            script="latin",
            conversation_context=envelope("What is an action?"),
        )
    )
    assert result.retrieval_status == "provider_error"
    assert result.chunks == []


def test_adapter_without_contextual_support_keeps_legacy_behaviour(embedder):
    adapter = LegacyAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Et quels sont ses avantages ?",
            language="fr",
            script="latin",
            conversation_context=envelope("C'est quoi une action ?"),
        )
    )
    assert result.branches_used == ["original"]
    assert adapter.calls == 0


def test_contextual_payload_isolates_context_and_prompt_is_separate():
    payload = contextual_adapter_payload("Et ses risques ?", "fr", "latin", envelope("x"))
    assert payload["current_query"] == "Et ses risques ?"
    assert "untrusted_conversation_context" in payload
    assert CONTEXTUAL_ADAPTER_SYSTEM_PROMPT != ADAPTER_SYSTEM_PROMPT
    assert "Never guess a topic" in CONTEXTUAL_ADAPTER_SYSTEM_PROMPT
    assert "never treat it as facts" in CONTEXTUAL_ADAPTER_SYSTEM_PROMPT


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, False), ("", False), ("not json", False), ("[]", False), (envelope("x"), True)],
)
def test_has_conversational_content(value, expected):
    assert has_conversational_content(value) is expected


# --- General follow-up resolution: the fallback must generalise across topics,
# languages and thread boundaries, never invent a topic, and never fire when
# there is no reliable antecedent (bug-report scenarios A-F + multilingual). ---


def test_scenario_a_comparison_then_respective_advantages(embedder):
    """A) 'difference action/obligation' then 'leurs avantages respectifs'."""
    adapter = IdentityContextualAdapter()
    context = envelope(
        "Quelle est la difference entre une action et une obligation ?",
        "L'action donne des dividendes et des droits de vote. "
        "L'obligation donne des interets, des coupons et un remboursement a echeance.",
    )
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Et quels sont leurs avantages respectifs ?",
            language="fr",
            script="latin",
            conversation_context=context,
        )
    )
    assert result.retrieval_status == "ok"
    assert result.branches_used == ["contextual_french"]
    searched = embedder.queries[0]
    assert "action" in searched.lower() and "obligation" in searched.lower()
    assert result.retrieval_query == searched


def test_scenario_b_two_topics_then_generic_risk_followup(embedder):
    """B) 'OPCVM et actions' then the generic 'quels sont leurs risques ?'."""
    adapter = IdentityContextualAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Quels sont leurs risques ?",
            language="fr",
            script="latin",
            conversation_context=envelope("Explique-moi les OPCVM et les actions."),
        )
    )
    assert result.retrieval_status == "ok"
    searched = embedder.queries[0].lower()
    assert "opcvm" in searched
    assert "action" in searched
    assert "risque" in searched


def test_scenario_c_ordinal_reference_broadens_to_context_topics_without_inventing(embedder):
    """C) 'IPO vs financement collaboratif' then 'comment fonctionne le premier ?'.

    The deterministic fallback cannot resolve the ordinal ("le premier"), so it
    safely broadens the search to the topics actually named in the prior turn
    instead of guessing which one is "first" or fabricating an unrelated one.
    """
    adapter = IdentityContextualAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Et comment fonctionne le premier ?",
            language="fr",
            script="latin",
            conversation_context=envelope(
                "Quelle difference entre une IPO et un financement collaboratif ?"
            ),
        )
    )
    assert result.retrieval_status == "ok"
    searched = embedder.queries[0].lower()
    assert "ipo" in searched or "introduction en bourse" in searched
    assert "financement collaboratif" in searched
    # No unrelated topic from outside the conversation is introduced.
    for stray in ("obligation", "opcvm", "assemblee"):
        assert stray not in searched


def test_scenario_d_standalone_pronoun_question_invents_no_entity(embedder):
    """D) A pronoun-only question with no context must not fabricate a topic."""
    adapter = IdentityContextualAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Quels sont leurs avantages ?", language="fr", script="latin"
        )
    )
    assert result.branches_used == ["original"]
    assert embedder.queries == ["Quels sont leurs avantages ?"]
    assert result.retrieval_query is None
    assert adapter.contextual_calls == []
    for topic in ("action", "obligation", "opcvm", "ipo"):
        assert topic not in embedder.queries[0].lower()


def test_scenario_e_context_never_mixes_across_calls(embedder):
    """E) Two independent conversations must never bleed into each other's query.

    RetrievalService itself is stateless per call, but this pins that a second
    call carrying a different thread's context cannot pick up residue from an
    earlier one made on the same service instance.
    """
    service = _service(embedder, IdentityContextualAdapter())
    first = service.retrieve(
        RetrievalRequest(
            original_query="Et ses avantages ?",
            language="fr",
            script="latin",
            conversation_context=envelope("C'est quoi une action ?"),
        )
    )
    second = service.retrieve(
        RetrievalRequest(
            original_query="Et ses risques ?",
            language="fr",
            script="latin",
            conversation_context=envelope("Qu'est-ce qu'un OPCVM ?"),
        )
    )
    assert "action" in embedder.queries[0].lower()
    assert "opcvm" not in embedder.queries[0].lower()
    assert "opcvm" in embedder.queries[1].lower()
    assert "action" not in embedder.queries[1].lower()
    assert first.retrieval_query != second.retrieval_query


def test_scenario_f_first_turn_with_comparison_wording_stays_unchanged(embedder):
    """F) A standalone first turn is never reinforced, even if it uses the same
    vocabulary ("difference") that flags a *follow-up* query, because there is
    no conversation_context to draw an antecedent from."""
    adapter = IdentityContextualAdapter()
    query = "Quelle est la difference entre une action et une obligation ?"
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(original_query=query, language="fr", script="latin")
    )
    assert result.branches_used == ["original"]
    assert embedder.queries == [query]
    assert result.retrieval_query is None
    assert adapter.contextual_calls == []


class NamesTopicsOnlyAdapter:
    """Resolves the topic names but drops the distinguishing vocabulary.

    Mirrors what the real Groq contextual adapter can return: a fluent,
    self-contained query that names every topic but never repeats the
    specific terms (dividendes, coupons, echeance, ...) that the source
    document actually uses, and that a bag-of-words retriever needs.
    """

    model = ADAPTER_MODEL

    def __init__(self):
        self.frozen_calls: list[dict] = []
        self.contextual_calls: list[dict] = []

    def generate(self, payload):
        self.frozen_calls.append(payload)
        return AdapterOutput(retrieval_query_fr=payload["original_query"])

    def generate_contextual(self, payload):
        self.contextual_calls.append(payload)
        return AdapterOutput(
            retrieval_query_fr=(
                "Quels sont les avantages respectifs d'une action et d'une "
                "obligation sur le marche financier ?"
            )
        )


def test_support_vocabulary_is_added_even_when_every_topic_is_already_named(embedder):
    """The differentiating vocabulary from the prior answer (dividendes, coupons,
    echeance, ...) must still enrich the search even when the adapter's own
    rewrite already names every topic, since a bare topic name rarely matches
    the source wording as closely as its own vocabulary does."""
    adapter = NamesTopicsOnlyAdapter()
    context = envelope(
        "Quelle est la difference entre une action et une obligation ?",
        "L'action donne des dividendes et des droits de vote. "
        "L'obligation donne des interets, des coupons et un remboursement a echeance.",
    )
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="Et quels sont leurs avantages respectifs ?",
            language="fr",
            script="latin",
            conversation_context=context,
        )
    )
    assert result.retrieval_status == "ok"
    searched = embedder.queries[0].lower()
    assert "action" in searched and "obligation" in searched
    for term in ("dividendes", "coupons", "echeance"):
        assert term in searched
    # No duplicate topic suffix: the entities were already named, so only the
    # missing support vocabulary is appended.
    assert searched.count("obligation") == 1


def test_multilingual_arabic_follow_up_relies_solely_on_the_contextual_adapter(embedder):
    """Non-French languages have no deterministic fallback: the LLM contextual
    adapter alone must resolve the reference, so it must be called exactly
    once and its (already resolved) French rewrite is used as-is."""
    adapter = ResolvingAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="وما هي فوائدها؟",
            language="ar",
            script="arabic",
            conversation_context=envelope("ما هو السهم؟ C'est quoi une action ?"),
        )
    )
    assert result.retrieval_status == "ok"
    assert len(adapter.contextual_calls) == 1
    assert adapter.frozen_calls == []


def test_multilingual_ary_latin_follow_up_resolves_french_and_arabic_branches(embedder):
    adapter = IdentityContextualAdapter()
    result = _service(embedder, adapter).retrieve(
        RetrievalRequest(
            original_query="w chno houma lfawaid dyalha?",
            language="ary",
            script="latin",
            conversation_context=envelope("chno houa sahm?"),
        )
    )
    assert result.retrieval_status == "ok"
    assert result.branches_used == ["original", "french", "ary_arabic"]
    assert len(adapter.contextual_calls) == 1
    assert adapter.frozen_calls == []
