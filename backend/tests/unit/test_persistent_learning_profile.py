import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from app.database.base import Base
from app.graph.core import create_learning_profile_service
from app.learning import InMemoryLearningProfileStore, LearningProfileService, SharedLearningProfile
from app.persistence.database import PersistenceDatabase
from app.persistence.learning_profile_store import SqlAlchemyLearningProfileStore
from app.persistence.models import LearningProfileRecord
from app.persistence.thread_store import ConversationThreadStore


def make_service(database_url: str) -> tuple[PersistenceDatabase, LearningProfileService]:
    database = PersistenceDatabase(
        enabled=True,
        database_url=database_url,
        engine_factory=lambda url, **kwargs: create_engine(url, **kwargs),
    )
    Base.metadata.create_all(database.get_engine())
    thread_store = ConversationThreadStore(database)
    profile_store = SqlAlchemyLearningProfileStore(database, thread_store)
    return database, LearningProfileService(profile_store)


def full_profile() -> SharedLearningProfile:
    return SharedLearningProfile(
        learning_level="intermediate",
        level_source="diagnostic",
        quiz_history=[
            {
                "quiz_id": "quiz-1",
                "topic": "opcvm",
                "level": "intermediate",
                "score_percent": 80.0,
                "correct_count": 4,
                "total_questions": 5,
                "completed_at": "2026-01-02T03:04:05Z",
            }
        ],
        completed_topics=["stocks"],
        topics_mastered=["bonds"],
        topics_to_review=["market_orders"],
        completed_modules=["module-1"],
        current_learning_path="capital-markets-foundations",
        last_quiz_score=80.0,
        diagnostic_completed=True,
    )


def test_all_profile_fields_round_trip(tmp_path) -> None:
    database, service = make_service(f"sqlite:///{tmp_path / 'profile.db'}")
    expected = full_profile()

    assert service.store.save("all-fields", expected) == expected
    assert service.get_profile("all-fields") == expected
    database.dispose()


def test_persistent_default_matches_in_memory_default(tmp_path) -> None:
    database, service = make_service(f"sqlite:///{tmp_path / 'defaults.db'}")

    assert service.get_profile("new-thread") == InMemoryLearningProfileStore().get("new-thread")
    database.dispose()


def test_profile_update_round_trip_uses_learning_profile_service(tmp_path) -> None:
    database, service = make_service(f"sqlite:///{tmp_path / 'update.db'}")

    service.set_level("updated", "intermediate", "diagnostic")
    service.mark_diagnostic_completed("updated")
    service.mark_module_completed("updated", "module-1")
    service.mark_topic_completed("updated", "stocks")
    service.set_learning_path("updated", "path-1")

    reloaded = service.get_profile("updated")
    assert reloaded.learning_level == "intermediate"
    assert reloaded.diagnostic_completed is True
    assert reloaded.completed_modules == ["module-1"]
    assert reloaded.completed_topics == ["stocks"]
    assert reloaded.current_learning_path == "path-1"
    database.dispose()


def test_profile_survives_store_and_database_recreation(tmp_path) -> None:
    database_a, service_a = make_service(f"sqlite:///{tmp_path / 'restart.db'}")
    service_a.store.save("restart-thread", full_profile())
    database_a.dispose()

    database_b, service_b = make_service(f"sqlite:///{tmp_path / 'restart.db'}")
    assert service_b.get_profile("restart-thread") == full_profile()
    database_b.dispose()


def test_profiles_are_isolated_by_thread_id(tmp_path) -> None:
    database, service = make_service(f"sqlite:///{tmp_path / 'isolation.db'}")

    service.set_level("thread-A", "advanced", "manual")
    service.mark_topic_mastered("thread-A", "stocks")
    service.record_quiz_attempt(
        "thread-A",
        quiz_id="quiz-A",
        topic="stocks",
        level="advanced",
        score_percent=100.0,
        correct_count=1,
        total_questions=1,
    )

    profile_b = service.get_profile("thread-B")
    assert profile_b == SharedLearningProfile()
    assert service.get_profile("thread-A").topics_mastered == ["stocks"]
    database.dispose()


def test_profile_mutable_defaults_do_not_leak_between_threads(tmp_path) -> None:
    database, service = make_service(f"sqlite:///{tmp_path / 'mutable.db'}")

    profile_a = service.get_profile("thread-A")
    profile_a.completed_topics.append("stocks")
    service.store.save("thread-A", profile_a)

    assert service.get_profile("thread-B").completed_topics == []
    database.dispose()


def test_persistence_enabled_composition_is_lazy(monkeypatch) -> None:
    class EnabledSettings:
        persistence_enabled = True
        database_url = "sqlite:///:memory:"

    monkeypatch.setattr("app.graph.core.get_settings", lambda: EnabledSettings())
    service = create_learning_profile_service()

    assert isinstance(service.store, SqlAlchemyLearningProfileStore)
    assert service.store.database._engine is None


def test_persistence_disabled_composition_keeps_in_memory_store(monkeypatch) -> None:
    class DisabledSettings:
        persistence_enabled = False
        database_url = ""

    monkeypatch.setattr("app.graph.core.get_settings", lambda: DisabledSettings())
    service = create_learning_profile_service()

    assert isinstance(service.store, InMemoryLearningProfileStore)


class FakeProfileSession:
    def __init__(self, winner: LearningProfileRecord | None, error: BaseException) -> None:
        self.winner = winner
        self.error = error
        self.reads = 0
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def get(self, model, profile_key):
        self.reads += 1
        return None if self.reads == 1 else self.winner

    def add(self, record) -> None:
        pass

    def commit(self) -> None:
        self.commits += 1
        if self.commits == 1:
            raise self.error

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


class FakeThreadStore:
    def get_or_create(self, thread_id: str) -> None:
        pass


def make_profile_store(session: FakeProfileSession) -> SqlAlchemyLearningProfileStore:
    database = PersistenceDatabase(enabled=True, database_url="sqlite://")
    database._session_factory = lambda: session
    return SqlAlchemyLearningProfileStore(database, FakeThreadStore())


def profile_integrity_error(
    *, constraint_name: str | None, sqlstate: str = "23505"
) -> IntegrityError:
    class Diagnostic:
        pass

    original = RuntimeError("violation de contrainte")
    original.sqlstate = sqlstate
    original.diag = Diagnostic()
    original.diag.constraint_name = constraint_name
    return IntegrityError("insert", {}, original)


def test_first_profile_save_race_rolls_back_rereads_and_preserves_caller_state() -> None:
    winner = LearningProfileRecord(
        thread_id="raced-profile",
        learning_level="beginner",
        level_source="diagnostic",
        quiz_history=[],
        completed_topics=[],
        topics_mastered=[],
        topics_to_review=[],
        completed_modules=[],
        current_learning_path=None,
        last_quiz_score=None,
        diagnostic_completed=False,
    )
    session = FakeProfileSession(
        winner, profile_integrity_error(constraint_name="learning_profiles_pkey")
    )
    store = make_profile_store(session)
    expected = full_profile()

    result = store.save("raced-profile", expected)

    assert result == expected
    assert session.rollbacks >= 1
    assert session.commits == 2
    assert session.closed is True


def test_profile_race_uses_sqlstate_and_constraint_not_english_text() -> None:
    error = profile_integrity_error(constraint_name="learning_profiles_pkey")
    assert SqlAlchemyLearningProfileStore._is_profile_identity_conflict(error) is True


def test_unrelated_profile_unique_conflict_is_not_swallowed() -> None:
    error = profile_integrity_error(constraint_name="other_constraint")
    session = FakeProfileSession(None, error)

    with pytest.raises(IntegrityError):
        make_profile_store(session).save("profile", full_profile())

    assert session.rollbacks >= 1
    assert session.closed is True


def test_non_unique_profile_database_error_is_not_swallowed() -> None:
    error = profile_integrity_error(constraint_name="learning_profiles_pkey", sqlstate="23514")
    session = FakeProfileSession(None, error)

    with pytest.raises(IntegrityError):
        make_profile_store(session).save("profile", full_profile())

    assert session.rollbacks >= 1
    assert session.closed is True


def test_profile_race_without_winner_reraises_after_rollback() -> None:
    error = profile_integrity_error(constraint_name="learning_profiles_pkey")
    session = FakeProfileSession(None, error)

    with pytest.raises(IntegrityError):
        make_profile_store(session).save("profile", full_profile())

    assert session.rollbacks >= 1
    assert session.closed is True


def test_sqlite_profile_identity_fallback_is_driver_scoped() -> None:
    original = sqlite3.IntegrityError(
        "UNIQUE constraint failed: learning_profiles.thread_id"
    )
    error = IntegrityError("insert", {}, original)

    assert SqlAlchemyLearningProfileStore._is_profile_identity_conflict(error) is True
