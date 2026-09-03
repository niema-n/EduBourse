import re
import unicodedata
from collections import Counter

from app.multilingual.models import LanguageAnalysis, LanguageCode
from app.multilingual.normalizer import normalize_text
from app.multilingual.script_detector import count_scripts, detect_script
from app.multilingual.statistical_detector import (
    StatisticalDetectorUnavailable,
    predict_arabic,
    predict_latin,
)

LATIN_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+", re.IGNORECASE)
ARABIC_TOKEN_RE = re.compile(r"[\u0621-\u064a]+")
ARABIZI_DIGIT_RE = re.compile(r"[379]")
ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")

FINANCIAL_TERMS = {"opcvm", "masi", "ipo", "cisi", "etf"}

FRENCH_STRONG = {
    "action",
    "actions",
    "achetée",
    "acheté",
    "apprendre",
    "baisse",
    "baissé",
    "bourse",
    "catégories",
    "comment",
    "comprendre",
    "cotée",
    "différence",
    "existe",
    "fictifs",
    "fonctionne",
    "obligation",
    "portefeuille",
    "quoi",
    "quelle",
    "risques",
    "société",
    "titres",
}
FRENCH_WEAK = {
    "a",
    "ai",
    "au",
    "aux",
    "avec",
    "ce",
    "cette",
    "de",
    "des",
    "du",
    "est",
    "et",
    "il",
    "j",
    "je",
    "la",
    "le",
    "les",
    "pour",
    "une",
    "veux",
}
FRENCH_ACCENTS = set("éèêàùç")

ENGLISH_STRONG = {
    "ahead",
    "alright",
    "analysis",
    "beginner",
    "buy",
    "clear",
    "company",
    "details",
    "differently",
    "diversification",
    "do",
    "examples",
    "explain",
    "financial",
    "go",
    "guide",
    "important",
    "information",
    "investment",
    "management",
    "market",
    "mind",
    "money",
    "more",
    "not",
    "one",
    "portfolio",
    "reliable",
    "reduce",
    "risk",
    "safe",
    "say",
    "sorry",
    "shares",
    "simple",
    "stock",
    "stocks",
    "technical",
    "thanks",
    "understand",
    "useful",
    "volatility",
}
ENGLISH_WEAK = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "can",
    "could",
    "does",
    "for",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "like",
    "need",
    "of",
    "on",
    "or",
    "please",
    "should",
    "that",
    "the",
    "there",
    "to",
    "very",
    "want",
    "was",
    "what",
    "when",
    "where",
    "why",
    "would",
}

DARJA_LATIN_STRONG = {
    "achno",
    "ana",
    "bach",
    "bezzaf",
    "bghina",
    "bghit",
    "brit",
    "bzaf",
    "bchwiya",
    "ch7al",
    "chhal",
    "chkoun",
    "chkon",
    "chno",
    "chokran",
    "dial",
    "dirham",
    "dyal",
    "fhemt",
    "fih",
    "fin",
    "flous",
    "had",
    "hada",
    "hadi",
    "hadik",
    "hadok",
    "hadchi",
    "hiya",
    "howa",
    "ila",
    "jdid",
    "khass",
    "khassni",
    "khasni",
    "kifach",
    "kolchi",
    "lborsa",
    "lboursa",
    "lia",
    "lmajal",
    "lwe9t",
    "ma3ndich",
    "mabdit",
    "makanfhemch",
    "mazal",
    "n9der",
    "nbda",
    "nefhem",
    "nfhem",
    "nla9a",
    "nqra",
    "nsowel",
    "nta3lem",
    "nt3ellem",
    "safi",
    "sahbi",
    "sghir",
    "s3ib",
    "sou9",
    "wa9ila",
    "wa9t",
    "wach",
    "walakin",
    "7it",
    "3lach",
}
DARJA_LATIN_WEAK = {
    "f",
    "gal",
    "kan",
    "kay",
    "kayn",
    "kayna",
    "khatira",
    "li",
    "ma",
    "mn",
    "o",
    "souk",
    "taman",
}

DARJA_ARABIC_STRONG_RAW = {
    "اش",
    "اشنو",
    "اول",
    "بغيت",
    "بغينا",
    "بزاف",
    "بالدارجه",
    "باش",
    "خاصني",
    "ديال",
    "ديالي",
    "صاحبي",
    "صافي",
    "شحال",
    "شنو",
    "شكون",
    "شويه",
    "علاش",
    "فاش",
    "فهاد",
    "فين",
    "فيه",
    "كلشي",
    "كيفاش",
    "ليا",
    "ماشي",
    "ماعنديش",
    "مازال",
    "مفهمتش",
    "نقدر",
    "نقرا",
    "نلقي",
    "نلقا",
    "نتبع",
    "نتعلم",
    "نبدا",
    "نعرفو",
    "نفهم",
    "هاد",
    "هادا",
    "هادي",
    "هادو",
    "هاديك",
    "هادشي",
    "واش",
}
DARJA_ARABIC_WEAK_RAW = {"درهم", "ثمن", "خاص", "شي", "خسرت", "كيتبدل", "مغربي", "مشكله"}

MSA_STRONG_RAW = {
    "أجد",
    "أين",
    "الاستثمار",
    "البورصة",
    "التعلم",
    "السند",
    "السهم",
    "المؤشر",
    "المخاطر",
    "المحفظة",
    "المقصود",
    "بتنويع",
    "تنويع",
    "رأس",
    "سعر",
    "سوق",
    "لماذا",
    "ماذا",
    "مخاطر",
    "يمكنني",
    "يعمل",
    "يتغير",
}
MSA_WEAK_RAW = {"هو", "هي", "كيف", "ما"}

ARABIC_TRANSLATION_TABLE = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ة": "ه",
    }
)
MSA_STRONG = {token.translate(ARABIC_TRANSLATION_TABLE) for token in MSA_STRONG_RAW}
MSA_WEAK = {token.translate(ARABIC_TRANSLATION_TABLE) for token in MSA_WEAK_RAW}
DARJA_ARABIC_STRONG = {
    token.translate(ARABIC_TRANSLATION_TABLE) for token in DARJA_ARABIC_STRONG_RAW
}
DARJA_ARABIC_WEAK = {token.translate(ARABIC_TRANSLATION_TABLE) for token in DARJA_ARABIC_WEAK_RAW}


def _latin_tokens(text: str) -> list[str]:
    return [token.strip("'").lower() for token in LATIN_TOKEN_RE.findall(text) if token.strip("'")]


def _arabic_detection_form(text: str) -> str:
    without_marks = ARABIC_DIACRITICS_RE.sub("", text.replace("ـ", ""))
    return unicodedata.normalize("NFKC", without_marks).translate(ARABIC_TRANSLATION_TABLE)


def _arabic_tokens(text: str) -> list[str]:
    return ARABIC_TOKEN_RE.findall(_arabic_detection_form(text))


def _arabic_matching_tokens(tokens: list[str]) -> list[str]:
    matching_tokens = list(tokens)
    for token in tokens:
        if token in {"هادي", "هادا", "هادو", "هاديك"}:
            matching_tokens.append("هاد")
        if token.startswith("ديال") and len(token) > len("ديال"):
            matching_tokens.append("ديال")
        if token.startswith("وما") and len(token) > 3:
            matching_tokens.append(token[1:])
        for prefix in ("فال", "وال", "بال", "لل"):
            if token.startswith(prefix) and len(token) > len(prefix) + 2:
                matching_tokens.append("ال" + token[len(prefix) :])
        for prefix in ("و", "ف", "ب", "ل"):
            if token.startswith(prefix) and len(token) > 4:
                remainder = token[len(prefix) :]
                if remainder.startswith(("ما", "هاد", "ديال", "غادي", "غا")):
                    matching_tokens.append(remainder)
    return matching_tokens


def _msa_matching_tokens(tokens: list[str]) -> list[str]:
    matching_tokens = list(tokens)
    for token in tokens:
        if token.startswith("ال") and len(token) > 4:
            matching_tokens.append(token[2:])
    return matching_tokens


def _token_score(tokens: list[str], strong: set[str], weak: set[str]) -> float:
    counts = Counter(tokens)
    return sum(3.0 * counts[token] for token in strong) + sum(1.0 * counts[token] for token in weak)


def _darija_latin_pattern_score(tokens: list[str]) -> float:
    score = 0.0
    for token in tokens:
        if ARABIZI_DIGIT_RE.search(token) and any(character.isalpha() for character in token):
            score += 1.7
        if token.startswith("gha") and len(token) >= 5:
            score += 2.4
        if token == "ghadi":
            score += 2.4
        if token.startswith(("kay", "kan")) and len(token) >= 5:
            score += 1.4
        if token.startswith("n") and len(token) >= 4 and token not in ENGLISH_STRONG:
            score += 0.8
        if token.startswith("ma") and token.endswith("ch") and len(token) >= 5:
            score += 2.4
    return score


def _english_pattern_score(text: str, tokens: list[str]) -> float:
    score = 0.0
    if re.search(r"\b(?:is|are|was|were|can|could|should|would)\b.+\?", text, re.IGNORECASE):
        score += 1.0
    if any(token.endswith("ing") for token in tokens):
        score += 0.6
    return score


def _french_pattern_score(text: str, tokens: list[str]) -> float:
    score = 0.0
    lower_text = text.lower()
    if any(character in lower_text for character in FRENCH_ACCENTS):
        score += 1.8
    if re.search(r"\b(?:j|c|n|l|d)'", lower_text):
        score += 1.3
    if any(token in FRENCH_WEAK for token in tokens) and any(
        token.endswith(("tion", "ment")) for token in tokens
    ):
        score += 0.1
    return score


def _confidence(best_score: float, second_score: float, token_count: int) -> float:
    if best_score <= 0:
        return 0.12
    margin = max(0.0, best_score - second_score)
    evidence = min(0.48, best_score / (best_score + 8.0))
    separation = min(0.28, margin / (best_score + 3.0))
    length_bonus = min(0.10, token_count / 80.0)
    return round(min(0.98, 0.18 + evidence + separation + length_bonus), 2)


def _winner(scores: dict[LanguageCode, float], token_count: int) -> tuple[LanguageCode, float]:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_language, best_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0
    if best_score <= 0:
        return "fr", 0.12
    return best_language, _confidence(best_score, second_score, token_count)


def _latin_language(text: str, script: str, tokens: list[str]) -> tuple[LanguageCode, float]:
    darija_score = (
        _token_score(tokens, DARJA_LATIN_STRONG, DARJA_LATIN_WEAK)
        + _darija_latin_pattern_score(tokens)
    )
    english_score = (
        _token_score(tokens, ENGLISH_STRONG, ENGLISH_WEAK) + _english_pattern_score(text, tokens)
    )
    french_score = _token_score(tokens, FRENCH_STRONG, FRENCH_WEAK) + _french_pattern_score(
        text, tokens
    )

    if script == "mixed":
        darija_score += 0.4

    scores: dict[LanguageCode, float] = {
        "ary-latin": darija_score,
        "en": english_score,
        "fr": french_score,
    }
    return _winner(scores, len(tokens))


def _darija_arabic_pattern_score(tokens: list[str]) -> float:
    score = 0.0
    for index, token in enumerate(tokens):
        if token.startswith("غا") and len(token) >= 4:
            score += 2.5
        if token == "غادي":
            score += 2.5
        if token.startswith(("كي", "كن")) and len(token) >= 4:
            score += 1.5
        if token.startswith("ما") and token.endswith("ش") and len(token) >= 4:
            score += 2.4
        if token == "ما" and index + 1 < len(tokens) and tokens[index + 1].endswith("ش"):
            score += 2.4
        if token.endswith("تش") and len(token) >= 5:
            score += 2.0
    if tokens and tokens[0] in {"اش", "اشنو", "شنو", "شحال", "شكون", "فين", "علاش", "واش"}:
        score += 2.0
    return score


def _arabic_language(text: str) -> tuple[LanguageCode, float]:
    tokens = _arabic_tokens(text)
    darija_score, msa_score = _arabic_scores(tokens)

    scores: dict[LanguageCode, float] = {"ary-arabic": darija_score, "ar": msa_score}
    language, confidence = _winner(scores, len(tokens))
    if language == "fr":
        return "ar", confidence
    return language, confidence


def _arabic_scores(tokens: list[str]) -> tuple[float, float]:
    matching_tokens = _arabic_matching_tokens(tokens)
    msa_matching_tokens = _msa_matching_tokens(tokens)
    darija_score = (
        _token_score(matching_tokens, DARJA_ARABIC_STRONG, DARJA_ARABIC_WEAK)
        + _darija_arabic_pattern_score(matching_tokens)
    )
    msa_score = _token_score(msa_matching_tokens, MSA_STRONG, MSA_WEAK)
    return darija_score, msa_score


def _effective_latin_letter_count(text: str) -> int:
    return sum(len(token) for token in _latin_tokens(text) if token not in FINANCIAL_TERMS)


def _use_arabic_branch(script: str, normalized_text: str) -> bool:
    _, arabic_count = count_scripts(normalized_text)
    if arabic_count == 0:
        return False
    if script == "arabic":
        return True

    effective_latin_count = _effective_latin_letter_count(normalized_text)
    if effective_latin_count == 0 and arabic_count >= 3:
        return True

    arabic_tokens = _arabic_tokens(normalized_text)
    darija_score, msa_score = _arabic_scores(arabic_tokens)
    if darija_score >= 5.0 and darija_score > msa_score:
        return True

    latin_language, latin_confidence = _latin_language(
        normalized_text,
        script,
        _latin_tokens(normalized_text),
    )
    if latin_language in {"fr", "en"} and latin_confidence >= 0.55 and effective_latin_count >= 8:
        return False
    return arabic_count >= max(6, effective_latin_count * 0.75)


def _heuristic_detection(normalized_text: str, script: str) -> tuple[LanguageCode, float]:
    if _use_arabic_branch(script, normalized_text):
        return _arabic_language(normalized_text)
    return _latin_language(
        normalized_text,
        script,
        _latin_tokens(normalized_text),
    )


def _classifier_detection(normalized_text: str, script: str) -> tuple[LanguageCode, float]:
    if _use_arabic_branch(script, normalized_text):
        prediction = predict_arabic(normalized_text)
    else:
        prediction = predict_latin(normalized_text)
    return prediction.language, prediction.confidence


def _has_high_precision_darija_rule(normalized_text: str, language: LanguageCode) -> bool:
    if language == "ary-latin":
        tokens = _latin_tokens(normalized_text)
        return bool(
            {"chno", "kifach", "wach", "bghit", "bghina", "ghadi"} & set(tokens)
            or any(token.startswith("gha") and len(token) >= 5 for token in tokens)
        )
    if language == "ary-arabic":
        tokens = _arabic_matching_tokens(_arabic_tokens(normalized_text))
        token_set = set(tokens)
        if {"شنو", "كيفاش", "واش", "بغيت", "بغينا", "غادي"} & token_set:
            return True
        if any(token.startswith("غا") and len(token) >= 4 for token in tokens):
            return True
        return "كلشي" in token_set and any(token.startswith(("كي", "كن")) for token in tokens)
    return False


def _has_high_precision_msa_rule(normalized_text: str, language: LanguageCode) -> bool:
    if language != "ar":
        return False
    tokens = _arabic_tokens(normalized_text)
    darija_score, msa_score = _arabic_scores(tokens)
    if msa_score >= 5.0 and msa_score > darija_score + 1.0:
        return True
    has_split_darija_negation = any(
        token == "ما" and index + 1 < len(tokens) and tokens[index + 1].endswith("ش")
        for index, token in enumerate(tokens)
    )
    if tokens and tokens[0] == "ما" and darija_score <= 1.0 and not has_split_darija_negation:
        return True
    return False


def _is_ambiguous_input(normalized_text: str) -> bool:
    tokens = _latin_tokens(normalized_text)
    if not tokens and not _arabic_tokens(normalized_text):
        return True
    return bool(tokens) and all(token in FINANCIAL_TERMS or token.isdigit() for token in tokens)


def detect_language(text: str) -> LanguageAnalysis:
    normalized_text = normalize_text(text)
    script = detect_script(normalized_text)
    heuristic_language, heuristic_confidence = _heuristic_detection(normalized_text, script)

    if (
        _is_ambiguous_input(normalized_text)
        or heuristic_confidence >= 0.92
        or _has_high_precision_darija_rule(normalized_text, heuristic_language)
        or _has_high_precision_msa_rule(normalized_text, heuristic_language)
    ):
        language, confidence = heuristic_language, heuristic_confidence
    else:
        try:
            language, confidence = _classifier_detection(normalized_text, script)
        except StatisticalDetectorUnavailable:
            language, confidence = heuristic_language, heuristic_confidence

    return LanguageAnalysis(
        language=language,
        script=script,
        normalized_text=normalized_text,
        confidence=confidence,
    )
