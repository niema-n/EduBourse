"""Storage boundary for learning profiles."""

from copy import deepcopy
from typing import Protocol

from app.learning.models import SharedLearningProfile


class LearningProfileStore(Protocol):
    def get(self, profile_key: str) -> SharedLearningProfile: ...

    def save(self, profile_key: str, profile: SharedLearningProfile) -> SharedLearningProfile: ...


class InMemoryLearningProfileStore:
    """Session-oriented store; persistent user identity is intentionally not assumed."""

    def __init__(self) -> None:
        self._profiles: dict[str, SharedLearningProfile] = {}

    def get(self, profile_key: str) -> SharedLearningProfile:
        if not profile_key.strip():
            raise ValueError("profile_key must not be blank")
        return deepcopy(self._profiles.get(profile_key, SharedLearningProfile()))

    def save(self, profile_key: str, profile: SharedLearningProfile) -> SharedLearningProfile:
        if not profile_key.strip():
            raise ValueError("profile_key must not be blank")
        self._profiles[profile_key] = deepcopy(profile)
        return deepcopy(profile)
