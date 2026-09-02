import re

from app.multilingual.models import LanguageAnalysis, LanguageCode
from app.multilingual.normalizer import normalize_text
from app.multilingual.script_detector import detect_script

TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.IGNORECASE)
ARABIZI_DIGIT_RE = re.compile(r"[379]")

FINANCIAL_TERMS = {"opvcm", "opcvm", "masi", "ipo", "cisi", "etf"}

DARJA_LATIN_MARKERS = {
    "achno",
    "bghit",
    "ch7al",
    "chno",
    "dial",
    "dyal",
    "fih",
    "fin",
    "hiya",
    "howa",
    "kan",
    "kay",
    "kayn",
    "kayna",
    "kaytbedel",
    "kifach",
    "lborsa",
    "n9der",
    "nla9a",
    "nt3ellem",
    "nta3lem",
    "sou9",
    "wach",
    "3lach",
}

DARJA_ARABIC_MARKERS = {
    "آش",
    "اشنو",
    "بغيت",
    "ديال",
    "شنو",
    "علاش",
    "فين",
    "فاش",
    "فهاد",
    "فيه",
    "كاين",
    "كاينة",
    "كيتبدل",
    "كيفاش",
    "نقدر",
    "واش",
    "هاد",
    "هادشي",
}

MSA_MARKERS = {
    "الاستثمار",
    "الفرق",
    "السند",
    "السهم",
    "البورصة",
    "المخاطر",
    "المؤشر",
    "رأس",
    "سوق",
    "كيف",
    "ما",
    "ماذا",
    "هو",
    "هي",
    "يعمل",
}

FRENCH_MARKERS = {
    "action",
    "apprendre",
    "bourse",
    "comment",
    "cotée",
    "différence",
    "est",
    "fonctionne",
    "je",
    "les",
    "obligation",
    "quoi",
    "quelle",
    "quels",
    "risques",
    "société",
    "une",
    "veux",
}

ENGLISH_MARKERS = {
    "about",
    "are",
    "bond",
    "difference",
    "does",
    "how",
    "investing",
    "learn",
    "market",
    "risks",
    "stock",
    "stocks",
    "the",
    "want",
    "what",
    "work",
}


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _score(tokens: list[str], markers: set[str]) -> int:
    return sum(1 for token in tokens if token in markers)


def _contains_arabizi_signal(text: str, tokens: list[str]) -> bool:
    if not ARABIZI_DIGIT_RE.search(text):
        return False
    return any(token in DARJA_LATIN_MARKERS for token in tokens) or len(tokens) <= 4


def _latin_language(text: str, script: str, tokens: list[str]) -> tuple[LanguageCode, float]:
    darja_score = _score(tokens, DARJA_LATIN_MARKERS)
    french_score = _score(tokens, FRENCH_MARKERS)
    english_score = _score(tokens, ENGLISH_MARKERS)
    non_financial_tokens = [token for token in tokens if token not in FINANCIAL_TERMS]

    if darja_score >= 2 or (darja_score >= 1 and _contains_arabizi_signal(text, tokens)):
        return "ary-latin", min(0.99, 0.70 + darja_score * 0.08)
    if darja_score >= 1 and french_score == 0 and english_score <= 1:
        return "ary-latin", 0.72
    if english_score > french_score:
        return "en", min(0.96, 0.62 + english_score * 0.08)
    if french_score > english_score:
        return "fr", min(0.96, 0.62 + french_score * 0.08)
    if script == "mixed" and darja_score >= 1:
        return "ary-latin", 0.70
    if non_financial_tokens and (
        "'" in text or any(character in text.lower() for character in ("é", "è", "à", "ç"))
    ):
        return "fr", 0.45
    return ("en", 0.35) if any(token in {"risk", "stock"} for token in tokens) else ("fr", 0.35)


def _arabic_language(text: str) -> tuple[LanguageCode, float]:
    darja_score = sum(1 for marker in DARJA_ARABIC_MARKERS if marker in text)
    msa_score = sum(1 for marker in MSA_MARKERS if marker in text)

    if darja_score >= 1:
        return "ary-arabic", min(0.98, 0.76 + darja_score * 0.08)
    if msa_score >= 1:
        return "ar", min(0.94, 0.62 + msa_score * 0.06)
    return "ar", 0.35


def detect_language(text: str) -> LanguageAnalysis:
    normalized_text = normalize_text(text)
    script = detect_script(normalized_text)
    tokens = _tokens(normalized_text)

    has_arabic_text = any("\u0600" <= char <= "\u06ff" for char in normalized_text)
    if script in {"arabic", "mixed"} and has_arabic_text:
        language, confidence = _arabic_language(normalized_text)
        return LanguageAnalysis(
            language=language,
            script=script,
            normalized_text=normalized_text,
            confidence=confidence,
        )

    language, confidence = _latin_language(normalized_text, script, tokens)
    return LanguageAnalysis(
        language=language,
        script=script,
        normalized_text=normalized_text,
        confidence=confidence,
    )
