import re
import unicodedata
from collections import Counter

from app.multilingual.models import LanguageAnalysis, LanguageCode
from app.multilingual.normalizer import normalize_text
from app.multilingual.script_detector import count_scripts, detect_script

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
    "analysis",
    "beginner",
    "buy",
    "clear",
    "company",
    "examples",
    "explain",
    "financial",
    "guide",
    "investment",
    "market",
    "money",
    "portfolio",
    "reliable",
    "risk",
    "safe",
    "shares",
    "simple",
    "stock",
    "stocks",
    "technical",
    "thanks",
    "understand",
    "volatility",
}
ENGLISH_WEAK = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "could",
    "does",
    "for",
    "how",
    "i",
    "in",
    "is",
    "it",
    "like",
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
    "hadi",
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
    "nta3lem",
    "nt3ellem",
    "safi",
    "sahbi",
    "s3ib",
    "sou9",
    "wa9ila",
    "wa9t",
    "wach",
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
    "بغيت",
    "بغينا",
    "بزاف",
    "بالدارجه",
    "باش",
    "خاص",
    "خاصني",
    "ديال",
    "درهم",
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
    "هادشي",
    "واش",
}
DARJA_ARABIC_WEAK_RAW = {"شي", "ثمن", "خسرت", "كيتبدل", "مغربي", "مشكله"}

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


def _token_score(tokens: list[str], strong: set[str], weak: set[str]) -> float:
    counts = Counter(tokens)
    return sum(3.0 * counts[token] for token in strong) + sum(1.0 * counts[token] for token in weak)


def _darija_latin_pattern_score(tokens: list[str]) -> float:
    score = 0.0
    for token in tokens:
        if ARABIZI_DIGIT_RE.search(token) and any(character.isalpha() for character in token):
            score += 1.7
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
    if any(token.endswith(("tion", "ment")) for token in tokens):
        score += 0.4
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
    for token in tokens:
        if token.startswith(("كي", "كن")) and len(token) >= 4:
            score += 1.5
        if token.startswith("ن") and len(token) >= 4:
            score += 0.8
        if token.startswith("ما") and token.endswith("ش") and len(token) >= 4:
            score += 2.4
        if token.endswith("تش") and len(token) >= 5:
            score += 2.0
    if tokens and tokens[0] in {"اش", "اشنو", "شنو", "شحال", "شكون", "فين", "علاش", "واش"}:
        score += 2.0
    return score


def _arabic_language(text: str) -> tuple[LanguageCode, float]:
    tokens = _arabic_tokens(text)
    darija_score = (
        _token_score(tokens, DARJA_ARABIC_STRONG, DARJA_ARABIC_WEAK)
        + _darija_arabic_pattern_score(tokens)
    )
    msa_score = _token_score(tokens, MSA_STRONG, MSA_WEAK)

    scores: dict[LanguageCode, float] = {"ary-arabic": darija_score, "ar": msa_score}
    language, confidence = _winner(scores, len(tokens))
    if language == "fr":
        return "ar", confidence
    return language, confidence


def _use_arabic_branch(script: str, normalized_text: str) -> bool:
    latin_count, arabic_count = count_scripts(normalized_text)
    if arabic_count == 0:
        return False
    if script == "arabic":
        return True
    return arabic_count >= max(4, latin_count * 0.55)


def detect_language(text: str) -> LanguageAnalysis:
    normalized_text = normalize_text(text)
    script = detect_script(normalized_text)

    if _use_arabic_branch(script, normalized_text):
        language, confidence = _arabic_language(normalized_text)
    else:
        language, confidence = _latin_language(
            normalized_text,
            script,
            _latin_tokens(normalized_text),
        )

    return LanguageAnalysis(
        language=language,
        script=script,
        normalized_text=normalized_text,
        confidence=confidence,
    )
