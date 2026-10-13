"""Display-only translated previews on POST /api/v1/rag/search.

Fake retrieval and fake translator: neither BGE-M3 nor Groq is used.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.rag import require_retrieval_service
from app.main import app
from app.rag.preview_translation import get_preview_translator, translate_previews
from app.rag.retrieval_service import RetrievalResult, RetrievedChunk

ORIGINAL = "L'introduction en bourse permet à une entreprise de lever des fonds."
DARIJA = "الدخول للبورصة كيسمح للشركة تجمع الفلوس."
ENGLISH = "An initial public offering lets a company raise funds."
DARIJA_QUERY = "شنو هي البورصة؟"


class FakeRetrieval:
    def __init__(self):
        self.requests = []

    def retrieve(self, request):
        self.requests.append(request)
        chunk = RetrievedChunk(
            chunk_id="ammc-comprendre-les-ipo-p008-c001-abcdef01",
            source_id="ammc-comprendre-les-ipo",
            title="Comprendre les IPO",
            page=8,
            page_start=8,
            page_end=8,
            heading=None,
            text=ORIGINAL,
            rank=1,
            retrieval_score=0.383421,
            score_type="cosine_distance",
        )
        return RetrievalResult(
            original_query=request.original_query,
            language=request.language,
            script=request.script,
            policy_id="H1_LANGUAGE_ROUTED_V1",
            branches_used=["french"] if request.language != "fr" else ["original"],
            adapted_query_fr="Qu'est-ce que la bourse ?" if request.language != "fr" else None,
            chunks=[chunk],
            retrieval_status="ok",
        )


class FakeTranslator:
    def __init__(self, text=DARIJA, error=None):
        self.text = text
        self.error = error
        self.payloads = []

    def translate(self, system_prompt, payload):
        self.payloads.append(payload)
        if self.error:
            raise self.error
        items = [{"id": item["id"], "text": self.text} for item in payload["excerpts"]]
        return {"translations": items}


def _client(retrieval, translator):
    app.dependency_overrides[require_retrieval_service] = lambda: retrieval
    app.dependency_overrides[get_preview_translator] = lambda: translator
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.clear()


def _search(client, query):
    response = client.post("/api/v1/rag/search", json={"query": query, "top_k": 5})
    assert response.status_code == 200
    return response.json()


def test_darija_preview_is_separate_and_original_excerpt_is_untouched():
    retrieval, translator = FakeRetrieval(), FakeTranslator()
    body = _search(_client(retrieval, translator), DARIJA_QUERY)
    hit = body["results"][0]
    assert body["language"] == "ary" and body["script"] == "arabic"
    assert hit["excerpt"] == ORIGINAL
    assert hit["source_language"] == "fr"
    assert hit["translated_excerpt"] == DARIJA
    assert hit["translated_language"] == "ary"
    assert hit["translated_script"] == "arabic"
    assert hit["translation_status"] == "translated"
    # The translator received exactly the retrieved original, once, in one batch.
    assert len(translator.payloads) == 1
    assert translator.payloads[0]["excerpts"] == [{"id": "E1", "text": ORIGINAL}]
    assert "Darija" in translator.payloads[0]["target_language"]


def test_translation_never_reaches_retrieval_or_evidence_metadata():
    retrieval, translator = FakeRetrieval(), FakeTranslator()
    body = _search(_client(retrieval, translator), DARIJA_QUERY)
    hit = body["results"][0]
    assert retrieval.requests[0].original_query == DARIJA_QUERY
    for field in ("title", "source_id", "chunk_id", "heading", "excerpt", "authority"):
        assert DARIJA not in str(hit[field])
    assert body["retrieval_query"] == "Qu'est-ce que la bourse ?"
    assert DARIJA not in str(body["branches"])


def test_french_query_needs_no_translation_and_no_provider_call():
    retrieval, translator = FakeRetrieval(), FakeTranslator()
    client = _client(retrieval, translator)
    body = _search(client, "Comment fonctionne une introduction en bourse ?")
    hit = body["results"][0]
    assert hit["translation_status"] == "not_needed"
    assert hit["translated_excerpt"] is None
    assert hit["excerpt"] == ORIGINAL
    assert translator.payloads == []


def test_english_preview_is_labelled_with_its_language():
    retrieval, translator = FakeRetrieval(), FakeTranslator(text=ENGLISH)
    hit = _search(_client(retrieval, translator), "What is a stock?")["results"][0]
    assert hit["translation_status"] == "translated"
    assert hit["translated_language"] == "en" and hit["translated_script"] == "latin"
    assert hit["excerpt"] == ORIGINAL


@pytest.mark.parametrize(
    "translator",
    [FakeTranslator(error=RuntimeError("429")), FakeTranslator(text=ENGLISH), None],
    ids=["provider-error", "wrong-script-for-darija", "no-provider"],
)
def test_translation_failure_keeps_search_results_usable(translator):
    retrieval = FakeRetrieval()
    body = _search(_client(retrieval, translator), DARIJA_QUERY)
    hit = body["results"][0]
    assert hit["translation_status"] == "unavailable"
    assert hit["translated_excerpt"] is None
    assert hit["translated_language"] is None
    assert hit["excerpt"] == ORIGINAL
    assert hit["title"] == "Comprendre les IPO"


def test_mismatched_or_missing_ids_are_rejected_per_item():
    class PartialTranslator:
        def translate(self, system_prompt, payload):
            return {"translations": [{"id": "E9", "text": DARIJA}]}

    previews = translate_previews(PartialTranslator(), [ORIGINAL, ORIGINAL], "ary", "arabic")
    assert [preview.status for preview in previews] == ["unavailable", "unavailable"]


def test_response_still_exposes_no_paths_or_vectors_and_stays_read_only():
    client = _client(FakeRetrieval(), FakeTranslator())
    body = _search(client, DARIJA_QUERY)
    text = str(body)
    for forbidden in ("index_path", "file_path", "document_hash", "embedding", "/backend/"):
        assert forbidden not in text
    assert client.put("/api/v1/rag/search").status_code == 405
    assert client.delete("/api/v1/rag/search").status_code == 405


def test_preview_that_copies_the_french_source_is_not_labelled_translated():
    class CopyTranslator:
        def translate(self, system_prompt, payload):
            items = [{"id": item["id"], "text": item["text"]} for item in payload["excerpts"]]
            return {"translations": items}

    for language, script in (("ary", "latin"), ("en", "latin")):
        previews = translate_previews(CopyTranslator(), [ORIGINAL], language, script)
        assert previews[0].status == "unavailable"


def test_darija_latin_preview_mixing_some_french_terms_is_accepted():
    darija_latin = "L'introduction en bourse kat3ti l charika imkaniya bach tjme3 flous mn soug."

    class LatinDarija:
        def translate(self, system_prompt, payload):
            return {"translations": [{"id": "E1", "text": darija_latin}]}

    previews = translate_previews(LatinDarija(), [ORIGINAL], "ary", "latin")
    assert previews[0].status == "translated"
    assert previews[0].text == darija_latin


def test_retry_delay_is_bounded():
    from app.rag.preview_translation import MAX_RETRY_DELAY_SECONDS, _retry_delay

    class Response:
        def __init__(self, headers):
            self.headers = headers

    class RateLimited(Exception):
        def __init__(self, headers):
            super().__init__("429")
            self.response = Response(headers)

    assert _retry_delay(RateLimited({"retry-after": "120"})) == MAX_RETRY_DELAY_SECONDS
    assert _retry_delay(RateLimited({"retry-after": "2"})) == 2.0
    assert _retry_delay(RateLimited({})) == 3.0
    assert _retry_delay(RateLimited({"retry-after": "soon"})) == 3.0
