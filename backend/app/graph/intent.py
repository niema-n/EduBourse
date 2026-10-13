"""Offline local intent models used by the J3 graph."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from threading import Lock
from typing import Any

import joblib

ARTIFACT_DIR = Path(__file__).with_name("artifacts")
SECURITY_ARTIFACT = ARTIFACT_DIR / "security_intent.joblib"
ROUTER_ARTIFACT = ARTIFACT_DIR / "business_router.joblib"


def normalize_text(text: str) -> str:
    """Normalize casing, accents, and French apostrophe elisions for inference."""
    text = unicodedata.normalize("NFKC", text.casefold()).replace("\u2019", "'")
    text = re.sub(r"\b([ldjctnm]'|d')(?=\w)", r"\1 ", text)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


class MissingSecurityArtifact(RuntimeError):
    pass


class MissingRouterArtifact(RuntimeError):
    pass


class LocalIntentModel:
    def __init__(self, path: Path, missing_error: type[RuntimeError]) -> None:
        self.path = path
        self.missing_error = missing_error
        self.bundle: dict[str, Any] | None = None
        self._load_lock = Lock()

    def load(self) -> dict[str, Any]:
        with self._load_lock:
            if self.bundle is None:
                if not isinstance(self.path, Path) or not self.path.is_file():
                    name = getattr(self.path, "name", "unknown")
                    raise self.missing_error(f"Missing local intent artifact: {name}")
                self.bundle = joblib.load(self.path)
        return self.bundle

    def predict(self, text: str) -> tuple[str, float, dict[str, float]]:
        bundle = self.load()
        model = bundle["model"]
        probabilities = model.predict_proba([normalize_text(text)])[0]
        classes = list(model.classes_)
        scores = {label: float(value) for label, value in zip(classes, probabilities, strict=True)}
        index = max(range(len(probabilities)), key=probabilities.__getitem__)
        return classes[index], float(probabilities[index]), scores


security_model = LocalIntentModel(SECURITY_ARTIFACT, MissingSecurityArtifact)
router_model = LocalIntentModel(ROUTER_ARTIFACT, MissingRouterArtifact)


# Explicit personalized investment selection ("the best investment for me",
# "what should I invest in"). Every pattern needs BOTH a recommendation/selection
# intent AND a personal reference, so profile or educational questions
# ("mon profil d'investisseur", "what is an investment?") are untouched. Patterns
# run on normalize_text output: casefolded, accents and Arabic hamza removed.
PERSONALIZED_SELECTION_PATTERNS = (
    # FR: meilleur + investissement/placement + pour moi (any order)
    r"(?=.*\bmeilleure?s?\b)(?=.*\b(?:investissements?|placements?|investir|placer)\b)"
    r"(?=.*\bpour moi\b)",
    # FR: dans quoi / où / quel ... dois-je|devrais-je ... investir|placer
    r"\b(?:dans quoi|ou|quels?|quelles?)\b.{0,25}\b(?:dois|devrais)\s*-?\s*je\b"
    r".{0,20}\b(?:investir|placer)\b",
    # FR: quel investissement/placement ... dois-je ... choisir|prendre|faire
    r"\b(?:quels?|quelles?)\s+(?:investissements?|placements?)\b.{0,25}"
    r"\b(?:dois|devrais)\s*-?\s*je\b.{0,15}\b(?:choisir|prendre|faire)\b",
    # FR: quel investissement/placement me recommandes-tu / me conseillez-vous
    r"\b(?:investissements?|placements?)\b.{0,25}"
    r"\bme\s+(?:recommandes?|recommandez|conseilles?|conseillez)\b",
    # EN: best + investment + for me (any order)
    r"(?=.*\bbest\b)(?=.*\b(?:investments?|invest)\b)(?=.*\bfor me\b)",
    # EN: what / where / which ... should I ... invest
    r"\b(?:what|where|which)\b.{0,25}\bshould i\b.{0,10}\binvest\b",
    # EN: which / what investment ... should I ... choose|pick|make|buy
    r"\b(?:which|what)\s+investments?\b.{0,25}\bshould i\b.{0,15}\b(?:choose|pick|make|buy)\b",
    # AR / Darija: افضل|احسن ... استثمار ... لي|ليا
    r"(?:افضل|احسن)\s*(?:\S+\s+){0,3}?(?:ال)?استثمار(?:ات)?\b.{0,20}(?:\bلي\b|\bليا\b)",
    # AR / Darija: ماذا|اين|فين|فاش|شنو|اش ... يجب|ينبغي|خاصني ... استثمر|نستثمر
    r"(?:ماذا|اين|فين|فاش|شنو|اش)\b.{0,25}(?:يجب|ينبغي|خاصني|خصني)\b.{0,20}(?:استثمر|نستثمر)",
    # Darija Latin: ahsan|a7san + investissement|istithmar + lia (any order)
    r"(?=.*\b(?:ahsan|a7san|ahssan)\b)(?=.*\b(?:investissement|istithmar|placement)\b)"
    r"(?=.*\b(?:lia|liya|lya)\b)",
    # Darija Latin: fach|fin|achmen ... khassni ... nstathmer|ninvesti
    r"\b(?:fach|fash|fin|achmen|ach)\b.{0,20}\b(?:khassni|khasni|khsni|khessni)\b"
    r".{0,20}\b(?:nstathmer|nstatmer|nstthmr|ninvesti)\b",
)


def personalized_selection_rule(text: str) -> bool:
    """Explicit request to pick an investment for the user, in FR/EN/AR/Darija."""
    normalized = normalize_text(text)
    return any(re.search(pattern, normalized) for pattern in PERSONALIZED_SELECTION_PATTERNS)


def high_precision_security_rule(text: str) -> bool:
    """Small defense layer for unambiguous direct financial instructions."""
    if personalized_selection_rule(text):
        return True
    normalized = normalize_text(text)
    direct = (
        r"\b(?:buy|acheter|vendre|sell)\b.{0,50}\b(?:for me|pour moi|now|maintenant)\b",
        r"\b(?:allocate|allouer|repartis|diviser)\b.{0,60}\b(?:my|mon|ma|mes|moi|flousi)\b",
        r"\b(?:what|which|quelle|quel)\b.{0,45}\b(?:buy|acheter|vendre|sell)\b",
        r"\b(?:should|dois)\b.{0,30}\b(?:buy|acheter|vendre|sell)\b",
        r"\b(?:choose|choisis)\b.{0,40}\b(?:stock|action|titre|saham)\b",
        r"\b(?:invest|investis|investir)\b.{0,40}\b(?:my|mes|mon|ma|moi|flousi|epargne|epargne)\b",
        r"\b(?:give me|donne moi)\b.{0,40}\b(?:stocks|actions|titres)\b",
        r"\b(?:likely to rise|va monter|ghadi ytla3|غادي يطلع|يرتفع)\b",
        r"\b(?:nchri|nbi3|nbi3|اشتر|اشري|نبيع|نشري)\b",
        r"\b(?:repartis|construis|investis)\b.{0,80}\b(?:action|actions|portefeuille|epargne|mon|mes)\b",
        r"\b(?:compare)\b.{0,60}\b(?:action|actions|stock|stocks)\b.{0,40}\b(?:acheter|buy|choisir)\b",
        r"\b(?:which|choose)\b.{0,50}\b(?:stock|stocks)\b.{0,30}\b(?:best|me|my|for)\b",
        r"(?:اشتر|أشتري|ابيع|أبيع|استثمر|قسم).{0,80}(?:سهم|الاسهم|أموالي|فلوسي|محفظة)",
        r"(?:أشتري|اشتر|نبيع|بيع).{0,40}(?:سهم|السهم|الاسهم)",
        r"(?:اشتري|اشتر|نبيع|بيع).{0,40}(?:سهم|السهم|الاسهم)",
        r"(?:سهم|السهم|الاسهم).{0,40}(?:اشتري|اشتر)",
        r"\bqssm\b.{0,60}\b(?:flousi|actions|obligations)\b",
    )
    return any(re.search(pattern, normalized) for pattern in direct)


def has_actionable_context(text: str) -> bool:
    """Identify personal/direct action context without deciding the label alone."""
    normalized = normalize_text(text)
    action = (
        r"\b(?:buy|acheter|vendre|sell|invest|investir|allocate|allouer|"
        r"choose|choisir|should|dois|recommande|best|meilleur|اشتر|نبيع|"
        r"نشري|استثمر|قسم)\b"
    )
    asset = (
        r"\b(?:stock|stocks|action|actions|bond|bonds|titre|titres|portfolio|"
        r"portefeuille|saham|سهم|السهم|الاسهم)\b"
    )
    personal = r"\b(?:my|me|for me|moi|mon|ma|mes|personnel|flousi|lia|لي|ليا|اموالي)\b"
    return (
        bool(re.search(action, normalized))
        and bool(re.search(asset, normalized))
        and bool(re.search(personal, normalized) or re.search(r"\d", normalized))
    )


def security_decision(text: str) -> tuple[bool, float, dict[str, float], str]:
    if high_precision_security_rule(text):
        return True, 1.0, {"safe": 0.0, "sensitive_personalized_financial_advice": 1.0}, "rule"
    normalized = normalize_text(text)
    if any(
        marker in normalized for marker in ("\u0633\u0647\u0645", "\u0627\u0644\u0633\u0647\u0645")
    ) and any(
        marker in normalized
        for marker in ("\u0627\u0634\u062a\u0631", "\u0627\u0634\u062a\u0631\u064a")
    ):
        return True, 1.0, {"safe": 0.0, "sensitive_personalized_financial_advice": 1.0}, "rule"
    label, confidence, scores = security_model.predict(text)
    threshold = float(security_model.load()["metadata"]["threshold"])
    if label == "sensitive_personalized_financial_advice" and not has_actionable_context(text):
        return False, confidence, scores, "model_safe_context"
    return (
        label == "sensitive_personalized_financial_advice" and confidence >= threshold,
        confidence,
        scores,
        "model",
    )


def route_decision(text: str) -> tuple[str, float, dict[str, float]]:
    label, confidence, scores = router_model.predict(text)
    threshold = float(router_model.load()["metadata"]["threshold"])
    return (label if confidence >= threshold else "fallback"), confidence, scores
