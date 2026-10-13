"""F2B regression: Darija written in Arabic script must not fall back to MSA or French.

Texts are written with explicit escapes so the expectations stay readable and
cannot be corrupted by an editor or terminal encoding.
"""

from __future__ import annotations

import pytest

from app.graph.language_adapter import normalize_business_language
from app.multilingual.detector import detect_language

# "chno hiya s-sahm?" - what is a share, in Moroccan Darija.
DARIJA_SHARE = "\u0634\u0646\u0648 \u0647\u064a \u0627\u0644\u0633\u0647\u0645\u061f"
# "chno hiya l-boursa?"
DARIJA_BOURSE = "\u0634\u0646\u0648 \u0647\u064a \u0627\u0644\u0628\u0648\u0631\u0635\u0629\u061f"
# "chno howa s-sahm?"
DARIJA_SHARE_MASC = "\u0634\u0646\u0648 \u0647\u0648 \u0627\u0644\u0633\u0647\u0645\u061f"
# "chno hiya l-as-hum f-l-boursa?"
DARIJA_SHARES_MARKET = (
    "\u0634\u0646\u0648 \u0647\u064a \u0627\u0644\u0623\u0633\u0647\u0645 "
    "\u0641\u0627\u0644\u0628\u0648\u0631\u0635\u0629\u061f"
)
# "ma howa s-sahm?" - Modern Standard Arabic control.
MSA_SHARE = "\u0645\u0627 \u0647\u0648 \u0627\u0644\u0633\u0647\u0645\u061f"
# "ma hiya l-boursa?" - Modern Standard Arabic control.
MSA_BOURSE = "\u0645\u0627 \u0647\u064a \u0627\u0644\u0628\u0648\u0631\u0635\u0629\u061f"


@pytest.mark.parametrize(
    "text",
    [DARIJA_SHARE, DARIJA_BOURSE, DARIJA_SHARE_MASC, DARIJA_SHARES_MARKET],
)
def test_darija_in_arabic_script_is_detected_as_ary_arabic(text):
    analysis = detect_language(text)
    assert analysis.language == "ary-arabic"
    assert analysis.script == "arabic"


@pytest.mark.parametrize("text", [MSA_SHARE, MSA_BOURSE])
def test_modern_standard_arabic_recall_is_preserved(text):
    analysis = detect_language(text)
    assert analysis.language == "ar"
    assert analysis.script == "arabic"


@pytest.mark.parametrize(
    ("text", "expected_language"),
    [
        (DARIJA_SHARE, "ary"),
        (DARIJA_BOURSE, "ary"),
        (DARIJA_SHARE_MASC, "ary"),
        (MSA_SHARE, "ar"),
    ],
)
def test_canonical_business_metadata_matches_the_chat_api_contract(text, expected_language):
    """The chat API maps detector labels exactly as app/api/chat.py does."""
    analysis = detect_language(text)
    business_language, business_script = normalize_business_language(
        analysis.language,
        None if analysis.language.startswith("ary-") else analysis.script,
    )
    assert business_language == expected_language
    assert business_script == "arabic"


def test_arabic_script_never_degrades_to_a_latin_language():
    for text in (DARIJA_SHARE, DARIJA_BOURSE, DARIJA_SHARE_MASC, MSA_SHARE, MSA_BOURSE):
        assert detect_language(text).language not in {"fr", "en", "ary-latin"}
