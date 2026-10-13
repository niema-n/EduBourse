"""Small deterministic policy for volatile financial-market questions."""

from __future__ import annotations

import re
from typing import Literal

_FRESHNESS_MARKERS = (
    "aujourd'hui",
    "aujourd hui",
    "maintenant",
    "actuellement",
    "actuel",
    "actuelle",
    "dernier cours",
    "cours de ",
    "today",
    "now",
    "current",
    "currently",
    "latest",
    "lyoma",
    "daba",
    "اليوم",
    "الآن",
    "حاليا",
    "حاليًا",
    "آخر سعر",
    "سعر السهم اليوم",
    "الثمن ديال",
    "السعر ديال",
)
_VOLATILE_PATTERNS = (
    r"\b(?:stock|share|action|saham)\b.{0,40}\b(?:price|quote)\b",
    r"\b(?:price|quote)\b.{0,40}\b(?:stock|share|action|saham)\b",
    r"\b(?:prix|cours|valeur)\b.{0,40}\b(?:action|titre|saham|sgtm|masi)\b",
    r"\b(?:action|titre|saham|sgtm|masi)\b.{0,40}\b(?:prix|cours|valeur)\b",
    r"\b(?:market|index)\s+(?:quote|level)\b",
    r"\btrading\s+volume\b",
    r"\bcurrent\s+ranking\b",
    r"\b(?:taman|cours)\s+dyal\b",
    r"\bch7al\s+taman\b",
    r"\b(?:سعر|ثمن)\b.{0,40}\b(?:السهم|سهم|ماسِي|ماسي)\b",
    r"\b(?:السهم|سهم|ماسِي|ماسي)\b.{0,40}\b(?:سعر|ثمن)\b",
)


# Index performance questions ("le MASI a augmenté de combien le 11/09") ask for
# a dated or recent market figure even without an explicit freshness marker.
_INDEX_TERMS = r"(?<!\w)(?:masi|madex|msi\s?20|ftse\s?cse|indice|index|ماسي|مازي|المؤشر|مؤشر)(?!\w)"
_MOVEMENT_TERMS = (
    r"(?<!\w)(?:augment\w*|baiss\w*|recul\w*|progress\w*|hausse|gagn\w*|perdu|chut\w*|"
    r"clôtur\w*|clotur\w*|rose|fell|gained|dropped|increased|decreased|tla3|hbet|"
    r"ارتفع|انخفض|تراجع)(?!\w)"
)
_DATE_TERMS = (
    r"(?<!\w)(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?|hier|avant-hier|cette\s+semaine|"
    r"lundi|mardi|mercredi|jeudi|vendredi|yesterday|this\s+week|monday|tuesday|"
    r"wednesday|thursday|friday|lbar7|البارح|أمس)(?!\w)"
)
_INDEX_FIGURE_PATTERNS = (
    rf"{_INDEX_TERMS}.{{0,60}}{_MOVEMENT_TERMS}",
    rf"{_MOVEMENT_TERMS}.{{0,60}}{_INDEX_TERMS}",
    rf"{_INDEX_TERMS}.{{0,60}}{_DATE_TERMS}",
    rf"{_DATE_TERMS}.{{0,60}}{_INDEX_TERMS}",
)

_LISTED_COLLECTION_MARKERS = (
    "quelles entreprises",
    "quelles sont les entreprises",
    "quelles sont les sociétés",
    "donne-moi la liste",
    "donne moi la liste",
    "liste des entreprises",
    "which companies",
    "what companies",
    "give me the list",
    "list of companies",
    "\u0645\u0627 \u0647\u064a \u0627\u0644\u0634\u0631\u0643\u0627\u062a",
    "\u0623\u0639\u0637\u0646\u064a \u0642\u0627\u0626\u0645\u0629",
    "\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0634\u0631\u0643\u0627\u062a",
    "chno homa charikat",
    "3tini liste dyal charikat",
    "\u0634\u0646\u0648 \u0647\u0645\u0627 \u0627\u0644\u0634\u0631\u0643\u0627\u062a",
)
_LISTED_MARKERS = (
    "cotée",
    "cotee",
    "cotés",
    "cotes",
    "listée",
    "listee",
    "listed",
    "en bourse",
    "à la bourse",
    "a la bourse",
    "boursa",
    "stock exchange",
    "\u0627\u0644\u0645\u062f\u0631\u062c\u0629",
    "\u0627\u0644\u0645\u0648\u062c\u0648\u062f\u0629",
    "\u0628\u0648\u0631\u0635\u0629",
    "\u0641\u0628\u0648\u0631\u0635\u0629",
    "\u0628\u0627\u0644\u0628\u0648\u0631\u0635\u0629",
)


def _is_listed_company_collection_request(text: str) -> bool:
    return any(marker in text for marker in _LISTED_COLLECTION_MARKERS) and any(
        marker in text for marker in _LISTED_MARKERS
    )


def requires_current_information(question: str, language: str, script: str) -> bool:
    """Return true for obvious current or volatile market-data requests."""
    del language, script
    text = " ".join(question.casefold().split())
    if _is_listed_company_collection_request(text):
        return True
    # Whole words only: "now" must not match "know", nor "current" "currency".
    if any(
        re.search(rf"(?<!\w){re.escape(marker.strip())}(?!\w)", text)
        for marker in _FRESHNESS_MARKERS
    ):
        return True
    if any(re.search(pattern, text) for pattern in _INDEX_FIGURE_PATTERNS):
        return True
    if any(re.search(pattern, text) for pattern in _VOLATILE_PATTERNS):
        return True
    return market_fact_intent(question) is not None


# ---------------------------------------------------------------------------
# Generic market-fact intent.
#
# No company, ticker or index is special-cased: the signals are words that ask
# for a market value, a time reference or a corporate event. The approved
# external source resolves the entity itself. All languages of the pipeline
# (fr, en, ar, ary arabic/latin) share one lexicon.
# ---------------------------------------------------------------------------

MarketFactIntent = Literal["current_data", "dated_data", "market_event", "listing_status"]


def _alternatives(*terms: str) -> str:
    return r"(?<!\w)(?:" + "|".join(terms) + r")(?!\w)"


_CURRENT_TIME = _alternatives(
    r"aujourd'hui",
    r"aujourd hui",
    r"maintenant",
    r"actuellement",
    r"en ce moment",
    r"ce jour",
    r"cette semaine",
    r"ce mois",
    r"cette ann[ée]e",
    r"derni[èe]re s[ée]ance",
    r"dernier cours",
    r"en temps r[ée]el",
    r"actuel(?:le)?",
    r"today",
    r"now",
    r"right now",
    r"currently",
    r"current",
    r"latest",
    r"this week",
    r"this month",
    r"last session",
    r"real[- ]time",
    r"lyoum",
    r"lyoma",
    r"lyouma",
    r"daba",
    r"had simana",
    r"had chhar",
    r"اليوم",
    r"الآن",
    r"الان",
    r"حاليا",
    r"حاليًا",
    r"دابا",
    r"هاد الأسبوع",
    r"هذا الأسبوع",
    r"هذا الشهر",
    r"آخر جلسة",
)

_MONTHS = (
    r"janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|"
    r"d[ée]cembre|january|february|march|april|may|june|july|august|september|october|"
    r"november|december|يناير|فبراير|مارس|أبريل|ماي|مايو|يونيو|يوليوز|يوليو|غشت|أغسطس|"
    r"شتنبر|سبتمبر|أكتوبر|نونبر|نوفمبر|دجنبر|ديسمبر"
)
_DATED_TIME = (
    r"(?<!\w)(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?|"
    rf"\d{{1,2}}\s+(?:{_MONTHS})(?:\s+\d{{4}})?|"
    r"hier|avant-hier|la veille|lundi|mardi|mercredi|jeudi|vendredi|samedi|"
    r"(?:la\s+)?semaine derni[èe]re|le mois dernier|"
    r"yesterday|last (?:week|month|friday|monday|tuesday|wednesday|thursday)|"
    r"monday|tuesday|wednesday|thursday|friday|"
    r"lbar7|lbare7|البارح|أمس|الأمس|الجمعة|الخميس|الأربعاء|الثلاثاء|الاثنين)(?!\w)"
)

# Words that by themselves ask for a quoted market value.
_MARKET_VALUE_STRONG = _alternatives(
    r"cours",
    r"prix",
    r"vaut",
    r"valait",
    r"variation",
    r"cl[ôo]tur\w*",
    r"ouverture",
    r"capitalisation",
    r"price",
    r"quote",
    r"worth",
    r"closing",
    r"opening",
    r"market cap",
    r"taman",
    r"سعر",
    r"ثمن",
    r"إغلاق",
    r"افتتاح",
    r"رسملة",
)
# Generic amount/movement words: only market values when a market anchor is present
# ("le match a gagné hier" is not a market question).
_MARKET_VALUE_WEAK = _alternatives(
    r"fait combien",
    r"combien",
    r"varie",
    r"hausse",
    r"baisse",
    r"augment\w*",
    r"diminu\w*",
    r"recul\w*",
    r"progress\w*",
    r"chut\w*",
    r"gagn\w*",
    r"perdu",
    r"performance",
    r"volume",
    r"niveau",
    r"valeur",
    r"rendement",
    r"level",
    r"close[ds]?",
    r"change",
    r"rose",
    r"fell",
    r"gained",
    r"lost",
    r"dropped",
    r"increased",
    r"decreased",
    r"how much",
    r"ch7al",
    r"chhal",
    r"dayr",
    r"daira",
    r"tla3",
    r"hbet",
    r"n9es",
    r"قيمة",
    r"كم",
    r"شحال",
    r"داير",
    r"دايرة",
    r"ارتفع",
    r"انخفض",
    r"تراجع",
    r"طلع",
    r"هبط",
    r"حجم",
    r"مستوى",
)
_MARKET_ANCHOR = _alternatives(
    r"masi",
    r"madex",
    r"msi ?20",
    r"ftse ?cse",
    r"indices?",
    r"index",
    r"bourse",
    r"boursi\w*",
    r"march[ée]s?",
    r"actions?",
    r"titres?",
    r"valeurs? mobili\w*",
    r"soci[ée]t[ée]s? cot\w*",
    r"opcvm",
    r"obligations?",
    r"stocks?",
    r"shares?",
    r"market",
    r"exchange",
    r"saham",
    r"boursa",
    r"ماسي",
    r"مازي",
    r"مؤشر",
    r"المؤشر",
    r"سهم",
    r"السهم",
    r"أسهم",
    r"الأسهم",
    r"بورصة",
    r"البورصة",
    r"السوق",
)
# Tickers are written in capitals (IAM, GTM, SGTM, ATW): checked on the raw text.
_TICKER = re.compile(r"(?<![A-Za-z])[A-Z]{2,6}(?![A-Za-z])")

_MARKET_EVENT = _alternatives(
    r"dividendes?",
    r"introduction(?:s)? en bourse",
    r"introdui\w*",
    r"ipo",
    r"offre publique",
    r"suspen\w*",
    r"reprise de (?:la )?cotation",
    r"augmentation de capital",
    r"communiqu[ée]s?",
    r"publication",
    r"r[ée]sultats",
    r"op[ée]ration(?:s)? sur titres",
    r"radiation",
    r"radi[ée]e?",
    r"retrait de la cote",
    r"cotation",
    r"dividends?",
    r"listing",
    r"delist\w*",
    r"trading halt",
    r"halted",
    r"capital increase",
    r"announcement",
    r"earnings",
    r"results",
    r"corporate action",
    r"tawzi3",
    r"arba7",
    r"أرباح",
    r"توزيع",
    r"إدراج",
    r"الإدراج",
    r"اكتتاب",
    r"تعليق",
    r"إيقاف",
    r"زيادة رأس المال",
    r"بلاغ",
    r"نتائج",
    r"شطب",
)

_RECENCY = (
    _alternatives(
        r"r[ée]cemment",
        r"r[ée]cents?",
        r"r[ée]cente",
        r"derni[èe]re?s?",
        r"annonc\w*",
        r"prochaine?s?",
        r"en cours",
        r"toujours",
        r"encore",
        r"recent(?:ly)?",
        r"latest",
        r"last",
        r"announced",
        r"upcoming",
        r"still",
        r"akhir",
        r"jdid",
        r"مؤخرا",
        r"الأخير",
        r"الأخيرة",
        r"آخر",
        r"أعلن\w*",
        r"المقبل",
        r"مازال",
        r"باقي",
    )
    + "|"
    + _CURRENT_TIME
    + "|"
    + _DATED_TIME
    + r"|(?<!\d)20\d{2}(?!\d)"
)

# Asking whether a given security is listed/suspended, not what "listed" means.
_LISTING_STATUS = (
    r"(?<!\w)(?:est[- ](?:elle|il)|sont[- ](?:elles|ils)|est)\s+(?:toujours\s+|encore\s+)?"
    r"(?:cot[ée]e?s?|list[ée]e?s?|suspendue?s?|radi[ée]e?s?)(?!\w)",
    r"(?<!\w)(?:is|are)\s+[\w&.' -]{1,40}\s+(?:still\s+)?"
    r"(?:listed|traded|suspended|delisted)(?!\w)",
    r"(?<!\w)(?:wach|wash)\s+.{1,40}(?:cot[ée]e?|mdraja|f(?:l)?bours[ae])(?!\w)",
    r"(?<!\w)هل\s+.{1,40}(?:مدرجة|مدرج|معلقة|مسعرة)",
    r"(?<!\w)واش\s+.{1,40}(?:مدرجة|مدرج|فالبورصة|فبورصة)",
)

# Definitional/explanatory phrasing stays on the educational path unless it
# carries an explicit time reference.
_DEFINITIONAL = _alternatives(
    r"c'est quoi",
    r"c est quoi",
    r"qu'est[- ]ce qu",
    r"qu est[- ]ce qu",
    r"que signifie",
    r"que veut dire",
    r"d[ée]finition",
    r"d[ée]finir",
    r"comment fonctionne",
    r"comment marche",
    r"comment se calcule",
    r"comment est calcul[ée]e?",
    r"explique[rz]?",
    r"what is an?",
    r"what are",
    r"what does .{1,30} mean",
    r"how does",
    r"how do",
    r"explain",
    r"define",
    r"definition",
    r"chno hiya",
    r"chno howa",
    r"chnou hiya",
    r"chnou howa",
    r"kifach",
    r"ما هو",
    r"ما هي",
    r"ما معنى",
    r"شنو هو",
    r"شنو هي",
    r"كيفاش",
    r"كيف يعمل",
    r"عرف",
)


def _normalize(question: str) -> str:
    return " ".join(question.replace("’", "'").casefold().split())


def market_fact_intent(question: str) -> MarketFactIntent | None:
    """Classify requests whose answer is a verifiable market fact.

    ``current_data`` / ``dated_data``: a market value tied to now or to a date.
    ``market_event``: a recent or specific corporate/market event.
    ``listing_status``: whether a security is listed, suspended or delisted.
    ``None``: stable educational content.
    """
    text = _normalize(question)
    anchored = re.search(_MARKET_ANCHOR, text) is not None or _TICKER.search(question) is not None
    has_value = re.search(_MARKET_VALUE_STRONG, text) is not None or (
        anchored and re.search(_MARKET_VALUE_WEAK, text) is not None
    )
    if has_value and re.search(_CURRENT_TIME, text):
        return "current_data"
    if has_value and re.search(_DATED_TIME, text):
        return "dated_data"
    if re.search(_DEFINITIONAL, text):
        return None
    if any(re.search(pattern, text) for pattern in _LISTING_STATUS):
        return "listing_status"
    if re.search(_MARKET_EVENT, text) and re.search(_RECENCY, text):
        return "market_event"
    return None


def requires_live_market_data(question: str) -> bool:
    """Current or dated market values: the static corpus can never answer them."""
    return market_fact_intent(question) in {"current_data", "dated_data"}


def requires_verified_market_facts(question: str, language: str, script: str) -> bool:
    """Facts that must come from an approved source, never from model memory."""
    return requires_current_information(question, language, script)
