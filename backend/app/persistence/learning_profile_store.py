"""SQLAlchemy storage for the existing shared learning profile."""

import sqlite3

from sqlalchemy.exc import IntegrityError

from app.learning.models import SharedLearningProfile
from app.persistence.database import PersistenceDatabase
from app.persistence.models import LearningProfileRecord
from app.persistence.thread_store import ConversationThreadStore


class SqlAlchemyLearningProfileStore:
    """Storage-only implementation of the existing LearningProfileStore contract."""

    def __init__(
        self, database: PersistenceDatabase, thread_store: ConversationThreadStore
    ) -> None:
        self.database = database
        self.thread_store = thread_store

    @staticmethod
    def _to_domain(record: LearningProfileRecord) -> SharedLearningProfile:
        return SharedLearningProfile.model_validate(
            {
                "learning_level": record.learning_level,
                "level_source": record.level_source,
                "quiz_history": record.quiz_history,
                "completed_topics": record.completed_topics,
                "topics_mastered": record.topics_mastered,
                "topics_to_review": record.topics_to_review,
                "completed_modules": record.completed_modules,
                "current_learning_path": record.current_learning_path,
                "last_quiz_score": record.last_quiz_score,
                "diagnostic_completed": record.diagnostic_completed,
            }
        )

    @staticmethod
    def _from_domain(thread_id: str, profile: SharedLearningProfile) -> LearningProfileRecord:
        values = profile.model_dump(mode="json")
        return LearningProfileRecord(thread_id=thread_id, **values)

    def get(self, profile_key: str) -> SharedLearningProfile:
        if not profile_key.strip():
            raise ValueError("profile_key must not be blank")
        with self.database.get_session_factory()() as session:
            record = session.get(LearningProfileRecord, profile_key)
            return SharedLearningProfile() if record is None else self._to_domain(record)

    def save(self, profile_key: str, profile: SharedLearningProfile) -> SharedLearningProfile:
        if not profile_key.strip():
            raise ValueError("profile_key must not be blank")
        validated = SharedLearningProfile.model_validate(profile.model_dump(mode="python"))
        self.thread_store.get_or_create(profile_key)
        session = self.database.get_session_factory()()
        try:
            record = session.get(LearningProfileRecord, profile_key)
            if record is None:
                record = self._from_domain(profile_key, validated)
                session.add(record)
            else:
                self._apply_domain(record, validated)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                if not self._is_profile_identity_conflict(exc):
                    raise
                record = session.get(LearningProfileRecord, profile_key)
                if record is None:
                    raise
                self._apply_domain(record, validated)
                session.commit()
            return self._to_domain(record)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _apply_domain(record: LearningProfileRecord, profile: SharedLearningProfile) -> None:
        values = profile.model_dump(mode="json")
        for field, value in values.items():
            setattr(record, field, value)

    @staticmethod
    def _is_profile_identity_conflict(error: IntegrityError) -> bool:
        original = error.orig
        sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
        message = str(original).lower()
        if sqlstate == "23505":
            constraint_name = getattr(getattr(original, "diag", None), "constraint_name", None)
            return constraint_name == "learning_profiles_pkey" or (
                constraint_name is None and "thread_id" in message
            )
        return isinstance(original, sqlite3.IntegrityError) and (
            "learning_profiles.thread_id" in message
            and "unique" in message
        )
