from __future__ import annotations

import re
import unicodedata

from app.graph.state import Route

TOKEN_RE = re.compile(r"[^\W_]+(?:['\u2019][^\W_]+)?", re.UNICODE)

DOMAIN_TERMS = {
    "action",
    "actions",
    "asset",
    "assets",
    "bourse",
    "bond",
    "bonds",
    "capital",
    "casablanca",
    "championnat",
    "cisi",
    "compliance",
    "diversification",
    "ebourse",
    "e",
    "elearning",
    "equity",
    "formation",
    "indice",
    "indices",
    "invest",
    "investment",
    "investissement",
    "investir",
    "learning",
    "marche",
    "obligation",
    "obligations",
    "order",
    "ordre",
    "orders",
    "parcours",
    "portfolio",
    "portefeuille",
    "quiz",
    "risk",
    "risque",
    "stock",
    "stocks",
    "support",
    "titre",
    "titres",
    "trading",
    "valeur",
    "acces",
    "apprendre",
    "beginner",
    "certification",
    "competition",
    "connexion",
    "connecter",
    "connect",
    "cours",
    "ecole",
    "login",
    "mot",
    "password",
    "inscription",
    "orientation",
    "questionnaire",
    "savings",
    "soutien",
    "test",
    "lborsa",
    "sou9",
    "flous",
    "flousi",
    "m3lomat",
    "t3lim",
    "nt3ellem",
    "nt3lem",
    "bghit",
    "qssm",
    "\u062a\u0643\u0648\u064a\u0646",
    "\u0646\u062a\u0639\u0644\u0645",
    "\u0627\u0644\u0628\u0648\u0631\u0635\u0629",
    "\u0633\u0647\u0645",
    "\u0627\u0644\u0633\u0647\u0645",
    "\u0627\u0633\u0647\u0645",
    "\u0627\u0644\u0627\u0633\u0647\u0645",
    "\u0627\u0633\u062a\u062b\u0645\u0627\u0631",
    "\u0645\u062d\u0641\u0638\u0629",
    "\u062a\u0639\u0644\u064a\u0645",
    "\u0645\u0628\u062a\u062f\u0626",
    "\u0645\u0633\u0627\u0631",
    "\u0627\u062e\u062a\u0628\u0627\u0631",
    "\u0627\u062e\u062a\u0628\u0627\u0631\u0627",
    "\u0634\u0647\u0627\u062f\u0629",
    "\u0643\u0644\u0645\u0629",
    "\u0627\u0644\u0645\u0631\u0648\u0631",
}

ROUTE_CUES: dict[Route, tuple[tuple[str, ...], ...]] = {
    "support_ecole": (
        ("mot", "de", "passe"),
        ("password",),
        ("login",),
        ("connexion",),
        ("connecter",),
        ("connect",),
        ("inscription",),
        ("compte",),
        ("account",),
        ("acces",),
        ("support",),
        ("\u0643\u0644\u0645\u0629", "\u0627\u0644\u0645\u0631\u0648\u0631"),
    ),
    "cisi": (
        ("cisi",),
        ("certification",),
        ("compliance",),
        ("professional", "certification"),
        ("\u0634\u0647\u0627\u062f\u0629",),
    ),
    "formation_elearning": (
        ("formation",),
        ("e", "learning"),
        ("elearning",),
        ("cours",),
        ("apprendre",),
        ("learning",),
        ("nt3ellem",),
        ("nt3lem",),
        ("bghit", "nt3ellem"),
        ("\u062a\u0643\u0648\u064a\u0646",),
        ("\u0646\u062a\u0639\u0644\u0645",),
        ("\u062f\u0648\u0631\u0629",),
    ),
    "quiz": (
        ("quiz",),
        ("questionnaire",),
        ("test",),
        ("questionne", "moi"),
        ("\u0627\u062e\u062a\u0628\u0627\u0631",),
        ("\u0627\u062e\u062a\u0628\u0627\u0631\u0627",),
        ("\u0627\u062e\u062a\u0628\u0631\u0646\u064a",),
    ),
    "championnat": (
        ("championnat",),
        ("e", "bourse"),
        ("ebourse",),
        ("competition",),
        ("concours",),
        ("portefeuille", "fictif"),
    ),
    "orientation": (
        ("orientation",),
        ("par", "ou", "commencer"),
        ("where", "should", "i", "start"),
        ("learning", "path"),
        ("learning", "journey"),
        ("debutant",),
        ("beginner",),
        ("mnin", "nbda"),
        ("\u0645\u0633\u0627\u0631",),
        ("\u0645\u0628\u062a\u062f\u0626",),
    ),
    "pedagogie": (
        ("action",),
        ("actions",),
        ("obligation",),
        ("obligations",),
        ("indice",),
        ("indices",),
        ("ordre",),
        ("orders",),
        ("bourse",),
        ("stock",),
        ("stocks",),
        ("diversification",),
        ("risk",),
        ("risque",),
        ("\u0633\u0647\u0645",),
        ("\u0627\u0633\u0647\u0645",),
        ("\u0627\u0644\u0628\u0648\u0631\u0635\u0629",),
    ),
}

FINANCIAL_ASSET_TERMS = {
    "action",
    "actions",
    "asset",
    "assets",
    "bond",
    "bonds",
    "equity",
    "equities",
    "instrument",
    "instruments",
    "obligation",
    "obligations",
    "portfolio",
    "portefeuille",
    "stock",
    "stocks",
    "titre",
    "titres",
    "valeur",
    "saham",
    "\u0633\u0647\u0645",
    "\u0627\u0633\u0647\u0645",
    "\u0633\u0646\u062f",
    "\u0633\u0646\u062f\u0627\u062a",
    "\u0645\u062d\u0641\u0638\u0629",
    "lborsa",
    "\u0627\u0644\u0628\u0648\u0631\u0635\u0629",
    "market",
    "markets",
    "marche",
    "\u0633\u0648\u0642",
    "\u0627\u0633\u0648\u0627\u0642",
}
DECISION_TERMS = {
    "acheter",
    "achete",
    "buy",
    "choisir",
    "choisis",
    "choose",
    "decide",
    "dois",
    "best",
    "better",
    "meilleur",
    "meilleure",
    "recommend",
    "recommande",
    "recommander",
    "should",
    "which",
    "quel",
    "quelle",
    "quoi",
    "vendre",
    "vend",
    "sell",
    "compare",
    "comparatif",
    "comparaison",
    "nchri",
    "nbi3",
    "nbi",
    "khayar",
    "khayarli",
    "\u0634\u0646\u0648",
    "\u0645\u0627\u0630\u0627",
    "\u0627\u0634\u062a\u0631\u064a",
    "\u0627\u0634\u062a\u0631\u064a\u0647",
    "\u0627\u0634\u062a\u0631",
    "\u0627\u0628\u064a\u0639",
    "\u0646\u0628\u064a\u0639",
    "\u0646\u0634\u0631\u064a",
}
ALLOCATION_TERMS = {
    "allocate",
    "allocation",
    "allouer",
    "repartis",
    "repartition",
    "divide",
    "diviser",
    "percentage",
    "pourcentage",
    "savings",
    "epargne",
    "construct",
    "construire",
    "portfolio",
    "portefeuille",
    "investis",
    "investir",
    "place",
    "placer",
    "qssm",
    "\u0642\u0633\u0645",
    "\u0646\u0642\u0633\u0645",
    "\u0627\u0633\u062a\u062b\u0645\u0631",
    "\u0627\u0633\u062a\u062b\u0645\u0631\u0648\u0627",
}
TIMING_TERMS = {
    "demain",
    "tomorrow",
    "rise",
    "rises",
    "rising",
    "monter",
    "montera",
    "hausser",
    "baisser",
    "fall",
    "likely",
    "probable",
    "prediction",
    "prevoir",
    "predict",
    "exit",
    "sortir",
    "maintenant",
    "now",
    "today",
    "\u063a\u062f\u0627",
    "\u063a\u062f\u064b\u0627",
    "\u064a\u0631\u062a\u0641\u0639",
    "\u064a\u0647\u0628\u0637",
    "\u063a\u0627\u062f\u064a",
    "\u064a\u0637\u0644\u0639",
    "\u064a\u0646\u0632\u0644",
}
PERSONAL_TERMS = {
    "me",
    "my",
    "for",
    "moi",
    "mon",
    "ma",
    "mes",
    "personnel",
    "personnelle",
    "j",
    "je",
    "i",
    "myself",
    "lia",
    "dyali",
    "\u0644\u064a",
    "\u0644\u064a\u0627",
    "\u0645\u0627\u0644\u064a",
    "\u0627\u0645\u0648\u0627\u0644\u064a",
    "\u0623\u0645\u0648\u0627\u0644\u064a",
    "flousi",
}
EDUCATIONAL_TERMS = {
    "what",
    "how",
    "explain",
    "generally",
    "why",
    "definition",
    "difference",
    "\u0645\u0627",
    "\u0647\u064a",
}


DOMAIN_TERMS.update({"\u0627\u0644\u0633\u0647\u0645", "\u0627\u0644\u0627\u0633\u0647\u0645"})
FINANCIAL_ASSET_TERMS.update(
    {"\u0627\u0644\u0633\u0647\u0645", "\u0627\u0644\u0627\u0633\u0647\u0645"}
)
ROUTE_CUES["pedagogie"] += (
    ("\u0627\u0644\u0633\u0647\u0645",),
    ("\u0627\u0644\u0627\u0633\u0647\u0645",),
)


def tokenize(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.casefold())
    ascii_folded = "".join(char for char in folded if not unicodedata.combining(char))
    return [token.casefold() for token in TOKEN_RE.findall(ascii_folded)]


def has_phrase(tokens: list[str], phrase: tuple[str, ...]) -> bool:
    width = len(phrase)
    return any(
        tuple(tokens[index : index + width]) == phrase for index in range(len(tokens) - width + 1)
    )


def has_any_phrase(tokens: list[str], phrases: tuple[tuple[str, ...], ...]) -> bool:
    return any(has_phrase(tokens, phrase) for phrase in phrases)


def is_sensitive_request(text: str, language: str = "unknown") -> bool:
    tokens = tokenize(text)
    token_set = set(tokens)
    assets = bool(token_set & FINANCIAL_ASSET_TERMS)
    decision = bool(token_set & DECISION_TERMS)
    allocation = bool(token_set & ALLOCATION_TERMS)
    timing = bool(token_set & TIMING_TERMS)
    personal = bool(token_set & PERSONAL_TERMS)
    explicit = has_any_phrase(
        tokens,
        (
            ("what", "should", "i"),
            ("which", "one", "should"),
            ("pour", "moi"),
            ("donne", "moi", "trois"),
            ("give", "me", "three"),
            ("choose", "for", "me"),
            ("choisis", "pour", "moi"),
            ("dois", "je"),
        ),
    )
    educational = bool(token_set & EDUCATIONAL_TERMS) and not bool(
        token_set
        & {"buy", "acheter", "vendre", "sell", "invest", "investir", "recommend", "recommande"}
    )
    allocation_request = allocation and (
        personal or any(char.isdigit() for char in text) or (decision and not educational)
    )
    actionable_without_asset = decision and bool(
        token_set & {"buy", "acheter", "vendre", "sell", "invest", "investir", "choose", "choisir"}
    )
    comparative_personal = (
        decision
        and personal
        and bool(token_set & {"which", "better", "best", "quel", "quelle", "meilleur", "compare"})
    )
    decision_request = (
        (assets and (decision or explicit)) or actionable_without_asset or comparative_personal
    ) and not educational
    timing_request = (assets or decision) and timing and not educational
    imperative_request = has_any_phrase(
        tokens,
        (
            ("buy", "this"),
            ("acheter", "pour", "moi"),
            ("invest", "my"),
            ("investis", "mes"),
            ("place", "mon"),
            ("\u0627\u0634\u062a\u0631",),
            ("\u0627\u0633\u062a\u062b\u0645\u0631",),
            ("\u0646\u0628\u064a\u0639",),
            ("\u0646\u0633\u062a\u062b\u0645\u0631",),
        ),
    )
    _ = language
    return allocation_request or decision_request or timing_request or imperative_request


def is_in_domain(text: str) -> bool:
    tokens = tokenize(text)
    token_set = set(tokens)
    return bool(token_set & DOMAIN_TERMS) or any(
        has_any_phrase(tokens, cues) for cues in ROUTE_CUES.values()
    )


def route_request(text: str) -> Route:
    tokens = tokenize(text)
    if not is_in_domain(text):
        return "out_of_domain"
    for route in (
        "support_ecole",
        "orientation",
        "formation_elearning",
        "cisi",
        "quiz",
        "championnat",
    ):
        if has_any_phrase(tokens, ROUTE_CUES[route]):
            return route
    if has_any_phrase(tokens, ROUTE_CUES["pedagogie"]):
        return "pedagogie"
    return "pedagogie"
