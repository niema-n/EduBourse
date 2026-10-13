"""Loader and validator for the authored Formation curriculum."""
# ruff: noqa: E501

from copy import deepcopy
from typing import Any

from app.formation.localized_content import (
    FORMATION_LOCALIZED_CONTENT,
    LOCALES,
)

_REQUIRED_FIELDS = ("title", "objective", "lesson", "key_points", "checkpoint")
_LEVELS = ("beginner", "intermediate", "advanced")
_LEGACY_TOPIC_IDS = (
    "market_basics", "stocks_bonds", "primary_secondary", "risk_return",
    "diversification", "indices", "orders", "moroccan_market",
)
_FORBIDDEN = (
    "market_basics",
    "stocks_bonds",
    "primary_secondary",
    "risk_return",
    "moroccan_market",
)


def validate_formation_content() -> None:
    if tuple(FORMATION_LOCALIZED_CONTENT) != _LEVELS:
        raise ValueError("Formation levels are incomplete or out of order")
    ids: set[str] = set()
    for level in _LEVELS:
        modules = FORMATION_LOCALIZED_CONTENT[level]
        if len(modules) != 8:
            raise ValueError(f"{level} must contain exactly eight modules")
        for module in modules:
            module_id = module.get("module_id")
            if not module_id or module_id in ids:
                raise ValueError("Formation module ids must be unique")
            ids.add(module_id)
            if set(module.get("locales", {})) != set(LOCALES):
                raise ValueError(f"{module_id} has incomplete locale coverage")
            for locale, content in module["locales"].items():
                if set(content) != set(_REQUIRED_FIELDS):
                    raise ValueError(f"{module_id}/{locale} has incomplete fields")
                if any(not isinstance(content[field], str) or not content[field].strip() for field in ("title", "objective", "lesson", "checkpoint")):
                    raise ValueError(f"{module_id}/{locale} has empty authored text")
                if not isinstance(content["key_points"], list) or len(content["key_points"]) < 2:
                    raise ValueError(f"{module_id}/{locale} needs at least two key points")
                if any(not isinstance(point, str) or not point.strip() for point in content["key_points"]):
                    raise ValueError(f"{module_id}/{locale} has an empty key point")
                visible = " ".join([content["title"], content["objective"], content["lesson"], *content["key_points"], content["checkpoint"]])
                if any(token in visible for token in _FORBIDDEN):
                    raise ValueError(f"{module_id}/{locale} exposes an internal slug")
                if "operates within public market rules" in visible or "s'inscrit dans des regles publiques" in visible:
                    raise ValueError(f"{module_id}/{locale} contains placeholder content")


validate_formation_content()


def modules_for(level: str) -> list[dict[str, Any]]:
    if level not in _LEVELS:
        raise ValueError("unknown formation level")
    return [
        {
            "module_id": f"{level}_{_LEGACY_TOPIC_IDS[index]}",
            "level": level,
            "index": index,
            "content": deepcopy(module["locales"]),
            "locales": deepcopy(module["locales"]),
        }
        for index, module in enumerate(FORMATION_LOCALIZED_CONTENT[level])
    ]
