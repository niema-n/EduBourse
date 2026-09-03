from __future__ import annotations

from typing import Protocol

from app.graph.state import LearnerProfile, TrainingRecord


class TrainingCatalog(Protocol):
    def search(self, profile: LearnerProfile) -> list[TrainingRecord]: ...


class EmptyTrainingCatalog:
    """Production port: real official catalog retrieval is a later milestone."""

    def search(self, profile: LearnerProfile) -> list[TrainingRecord]:
        return []


class FixtureTrainingCatalog:
    """Deterministic test fixture; these records are not real school offerings."""

    def __init__(self, records: list[TrainingRecord]) -> None:
        self.records = records

    def search(self, profile: LearnerProfile) -> list[TrainingRecord]:
        return list(self.records)


def match_training(
    profile: LearnerProfile, records: list[TrainingRecord]
) -> tuple[list[TrainingRecord], TrainingRecord | None]:
    level = profile.get("level", "debutant")
    goal = profile.get("learning_goal", "")
    weak_topics = set(profile.get("weak_topics", []))
    scored = []
    for record in records:
        score = int(record.get("level") == level)
        score += int(goal in record.get("goals", []))
        score += len(weak_topics.intersection(record.get("topics", [])))
        scored.append((score, record.get("id", ""), record))
    scored.sort(key=lambda item: (-item[0], item[1]))
    ordered = [record for _, _, record in scored]
    return ordered, ordered[0] if ordered else None
