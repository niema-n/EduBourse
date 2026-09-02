from app.multilingual.normalizer import normalize_text


def test_normalization_is_conservative() -> None:
    assert normalize_text("  chno   hiya lborsa ? ") == "chno hiya lborsa ?"


def test_normalization_preserves_arabizi_digits_and_terms() -> None:
    assert normalize_text("  wach   OPCVM fih risk 9? ") == "wach OPCVM fih risk 9?"


def test_normalization_does_not_translate() -> None:
    assert normalize_text("شنو هي البورصة؟") == "شنو هي البورصة؟"
