"""Offline local intent models used by the J3 graph."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
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

    def load(self) -> dict[str, Any]:
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


def high_precision_security_rule(text: str) -> bool:
    """Small defense layer for unambiguous direct financial instructions."""
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


def security_decision(text: str) -> tuple[bool, float, dict[str, float], str]:
    if high_precision_security_rule(text):
        return True, 1.0, {"safe": 0.0, "sensitive_personalized_financial_advice": 1.0}, "rule"
    normalized = normalize_text(text)
    if (
        any(
            marker in normalized
            for marker in ("\u0633\u0647\u0645", "\u0627\u0644\u0633\u0647\u0645")
        )
        and any(
            marker in normalized
            for marker in ("\u0627\u0634\u062a\u0631", "\u0627\u0634\u062a\u0631\u064a")
        )
    ):
        return True, 1.0, {"safe": 0.0, "sensitive_personalized_financial_advice": 1.0}, "rule"
    if re.search(r"\b(?:what is|explain|definition of|how does|difference between)\b", normalized):
        return (
            False,
            1.0,
            {"safe": 1.0, "sensitive_personalized_financial_advice": 0.0},
            "educational_rule",
        )
    label, confidence, scores = security_model.predict(text)
    threshold = float(security_model.load()["metadata"]["threshold"])
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
