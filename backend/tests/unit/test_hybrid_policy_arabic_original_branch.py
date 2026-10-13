"""P0: Arabic-script questions also search with the user's own wording.

The adapted French branch stays; the original query is added so an imperfect or
neighbouring French adaptation cannot silently hide the right corpus content.
Fusion reuses the existing RRF primitives, unchanged.
"""

import pytest

from app.rag.hybrid_policy import RRF_K, hybrid_branches, rrf_scores

ORIGINAL = "ما هو الاكتتاب العام؟"
FRENCH = "définition de l'offre publique à souscription"
ARY_ARABIC = "شنو هو الاكتتاب العام؟"


def _record(original=ORIGINAL, french=FRENCH, arabic=ARY_ARABIC):
    return {
        "original_query": original,
        "retrieval_query_fr": french,
        "retrieval_query_ary_arabic": arabic,
    }


def test_french_routing_is_unchanged():
    assert hybrid_branches("fr", "latin", _record(original="Qu'est-ce qu'une action ?")) == [
        ("original", "Qu'est-ce qu'une action ?")
    ]


def test_english_routing_is_unchanged():
    assert hybrid_branches("en", "latin", _record()) == [("french", FRENCH)]


@pytest.mark.parametrize(("language", "script"), [("ar", "arabic"), ("ary", "arabic")])
def test_arabic_script_keeps_french_and_adds_the_original_query(language, script):
    branches = hybrid_branches(language, script, _record())

    assert [name for name, _ in branches] == ["original", "french"]
    assert dict(branches)["original"] == ORIGINAL  # user wording reaches retrieval
    assert dict(branches)["french"] == FRENCH  # adapted branch preserved


def test_ary_latin_multi_branch_behaviour_is_preserved():
    branches = hybrid_branches("ary", "latin", _record(original="Chno howa lik'titab?"))

    assert [name for name, _ in branches] == ["original", "french", "ary_arabic"]
    assert dict(branches)["ary_arabic"] == ARY_ARABIC


@pytest.mark.parametrize(("language", "script"), [("ar", "arabic"), ("ary", "arabic")])
def test_identical_queries_are_deduplicated(language, script):
    """An adapter echoing the input must not make RRF count one ranking twice."""
    record = _record(original=ORIGINAL, french=f"  {ORIGINAL.upper()}  ")

    branches = hybrid_branches(language, script, record)

    assert [name for name, _ in branches] == ["original"]
    assert len({query for _, query in branches}) == len(branches)


def test_ary_latin_keeps_its_three_branches_even_when_texts_repeat():
    """The frozen ary/latin policy is untouched, including with an echoing adapter."""
    record = _record(original=ORIGINAL, french=ORIGINAL, arabic=ORIGINAL)

    assert [name for name, _ in hybrid_branches("ary", "latin", record)] == [
        "original",
        "french",
        "ary_arabic",
    ]


def test_unknown_language_script_still_rejected():
    with pytest.raises(ValueError):
        hybrid_branches("xx", "arabic", _record())


@pytest.mark.parametrize(("language", "script"), [("ar", "arabic"), ("ary", "arabic")])
def test_rrf_fusion_receives_both_arabic_branches(language, script):
    """Both rankings contribute: a chunk ranked only by one branch still scores."""
    branches = hybrid_branches(language, script, _record())
    assert len(branches) == 2

    original_ranking = [7, 1, 2]  # chunk 7 only found through the original query
    french_ranking = [1, 2, 3]
    scores = rrf_scores([original_ranking, french_ranking], RRF_K)

    assert scores[7] == pytest.approx(1.0 / (RRF_K + 1))
    assert scores[1] == pytest.approx(1.0 / (RRF_K + 2) + 1.0 / (RRF_K + 1))
    assert scores[3] == pytest.approx(1.0 / (RRF_K + 3))
