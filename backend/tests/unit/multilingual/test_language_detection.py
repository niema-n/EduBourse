import pytest

from app.multilingual.detector import detect_language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("C'est quoi une action ?", "fr"),
        ("Comment fonctionne une obligation ?", "fr"),
        ("C'est quoi une société cotée ?", "fr"),
        ("Quelle est la différence entre une obligation et une action ?", "fr"),
    ],
)
def test_detects_french(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("What is a stock?", "en"),
        ("How does a bond work?", "en"),
        ("What are the risks of investing in stocks?", "en"),
        ("I want to learn about the stock market.", "en"),
    ],
)
def test_detects_english(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ما هو السهم؟", "ar"),
        ("ما هي البورصة؟", "ar"),
        ("ما هي مخاطر الاستثمار؟", "ar"),
        ("كيف يعمل سوق رأس المال؟", "ar"),
    ],
)
def test_detects_standard_arabic(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("chno hiya lborsa?", "ary-latin"),
        ("achno howa sou9 lborsa?", "ary-latin"),
        ("bghit nt3ellem lborsa", "ary-latin"),
        ("wach OPCVM fih risk?", "ary-latin"),
        ("kifach n9der nt3ellem lborsa?", "ary-latin"),
        ("fin n9der nla9a formation?", "ary-latin"),
        ("ch7al kayn mn naw3 dyal actions?", "ary-latin"),
        ("3lach taman dyal action kaytbedel?", "ary-latin"),
    ],
)
def test_detects_darija_latin(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("شنو هي البورصة؟", "ary-arabic"),
        ("بغيت نتعلم البورصة", "ary-arabic"),
        ("واش الاستثمار فيه المخاطر؟", "ary-arabic"),
        ("كيفاش نقدر نتعلم البورصة؟", "ary-arabic"),
        ("فين نقدر نلقى تكوين؟", "ary-arabic"),
        ("علاش ثمن السهم كيتبدل؟", "ary-arabic"),
    ],
)
def test_detects_darija_arabic(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("wach OPCVM fih risk?", "ary-latin"),
        ("شنو هو MASI؟", "ary-arabic"),
        ("C'est quoi le MASI ?", "fr"),
        ("What is the MASI?", "en"),
    ],
)
def test_financial_terms_do_not_override_surrounding_language(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


def test_ambiguous_short_phrase_has_low_confidence() -> None:
    result = detect_language("MASI")

    assert result.language in {"fr", "en"}
    assert result.confidence is not None
    assert result.confidence <= 0.40


@pytest.mark.parametrize(
    "text",
    [
        "Thanks, that was very clear.",
        "Is technical analysis reliable?",
        "Please explain volatility in simple terms.",
        "I would like a simple beginner guide.",
    ],
)
def test_detects_natural_english_regressions(text: str) -> None:
    assert detect_language(text).language == "en"


@pytest.mark.parametrize(
    "text",
    [
        "wa9ila khassni nqra chwiya 9bel ma nbda",
        "hadchi s3ib bezzaf 3liya",
        "ana jdid f had lmajal",
        "chhal mn dirham khassni bach nbda?",
        "kolchi kayqol lbourse khatira",
        "makanfhemch had rendement o risque",
        "ma3ndich wa9t bach ntab3 lmarche kol yom",
        "safi fhemt, chokran bzaf",
    ],
)
def test_detects_darija_latin_regressions(text: str) -> None:
    assert detect_language(text).language == "ary-latin"


@pytest.mark.parametrize(
    "text",
    [
        "خاصني شي كتاب باش نتعلم",
        "شحال من درهم خاصني باش نبدا؟",
        "ماعنديش الوقت باش نتبع السوق",
        "صاحبي قال ليا خاص التنويع",
        "كلشي كيقول البورصة خطيرة",
        "بغينا نعرفو الفرق بين البنك والبورصة",
        "شكون لي كيراقب البورصة فالمغرب؟",
        "ماشي مشكل إلا خسرت شوية؟",
    ],
)
def test_detects_darija_arabic_regressions(text: str) -> None:
    assert detect_language(text).language == "ary-arabic"


@pytest.mark.parametrize(
    "text",
    [
        "ما هي البورصة؟",
        "كيف يمكنني التعلم؟",
        "أين أجد التكوين؟",
        "لماذا يتغير سعر السهم؟",
        "ما المقصود بتنويع المحفظة؟",
    ],
)
def test_standard_arabic_not_reclassified_as_darija(text: str) -> None:
    assert detect_language(text).language == "ar"


@pytest.mark.parametrize(
    "text",
    [
        "شنو هي البورصة؟",
        "كيفاش نقدر نتعلم؟",
        "فين نلقى التكوين؟",
        "علاش كيتبدل ثمن السهم؟",
        "بغيت نفهم البورصة",
    ],
)
def test_darija_arabic_not_reclassified_as_standard_arabic(text: str) -> None:
    assert detect_language(text).language == "ary-arabic"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Je veux comprendre la Bourse.", "fr"),
        ("Cette action a baissé de 3 %.", "fr"),
        ("Il existe 7 catégories.", "fr"),
        ("J'ai acheté 9 titres fictifs.", "fr"),
        ("bghit nefhem lboursa", "ary-latin"),
        ("7it l'bourse s3iba", "ary-latin"),
        ("ma3ndich wa9t", "ary-latin"),
        ("chhal khassni bach nbda", "ary-latin"),
    ],
)
def test_french_and_darija_latin_digit_regressions(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("wach OPCVM fih risk?", "ary-latin"),
        ("شنو هو MASI؟", "ary-arabic"),
        ("I want to understand السهم", "en"),
        ("Bonjour؟", "fr"),
        ("Le prix est ٥٠٠ dirhams", "fr"),
    ],
)
def test_code_switching_dominance(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("شَنو هي البورصة؟", "ary-arabic"),
        ("شـــنو هي البورصة؟", "ary-arabic"),
        ("مَا هُوَ السَّهْمُ؟", "ar"),
    ],
)
def test_arabic_diacritics_and_tatweel(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize("text", ["", " ", "?", "123", "😂", "---", "\n\t", "\ufeff"])
def test_edge_cases_do_not_crash_and_stay_low_confidence(text: str) -> None:
    result = detect_language(text)

    assert result.language in {"fr", "en", "ar", "ary-latin", "ary-arabic"}
    assert result.confidence is not None
    assert result.confidence <= 0.25


@pytest.mark.parametrize(
    "text",
    [
        "هادي أول مرة نسول على هاد الموضوع",
        "الحساب ديالي صغير",
        "أنا خدام وماعنديش بزاف ديال الوقت",
        "فالبورصة كاين بزاف ديال المفاهيم",
        "والسوق ديالي مازال ما فهمتوش",
    ],
)
def test_darija_arabic_clitic_handling(text: str) -> None:
    assert detect_language(text).language == "ary-arabic"


@pytest.mark.parametrize(
    "text",
    [
        "ghanjrb walakin b chwiya",
        "ghanbda b chi mablagh sghir",
        "ghadi nbda mn zero",
        "غانحاول نفهم شوية بشوية",
        "غادي نبدا من الصفر",
    ],
)
def test_darija_future_gha_forms(text: str) -> None:
    assert detect_language(text).language in {"ary-latin", "ary-arabic"}


@pytest.mark.parametrize(
    "text",
    [
        "كم من الوقت يلزم لرؤية نتيجة؟",
        "هل توجد نسخة مختصرة من الدليل؟",
        "أحتاج إلى نصيحة.",
        "ما نسبة المخاطر في هذا الاستثمار؟",
        "كيف يعمل النظام المالي؟",
        "ما معدل نمو السوق؟",
    ],
)
def test_standard_arabic_n_prefix_words_are_not_darija(text: str) -> None:
    assert detect_language(text).language == "ar"


@pytest.mark.parametrize(
    "text",
    [
        "Sorry, one more question if you do not mind.",
        "Investment management is important.",
        "This information is useful.",
        "Diversification can reduce risk.",
        "Alright, go ahead.",
        "Sorry, I did not understand that.",
        "Could you say that differently?",
    ],
)
def test_english_tion_ment_and_low_marker_sentences(text: str) -> None:
    assert detect_language(text).language == "en"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Je cherche des infos sur السوق المالي", "fr"),
        ("I need details about سوق الأسهم", "en"),
        ("بغيت نفهم stock market مزيان", "ary-arabic"),
        ("wach had ETF intéressant?", "ary-latin"),
    ],
)
def test_code_switching_uses_language_dominance(text: str, expected: str) -> None:
    assert detect_language(text).language == expected
