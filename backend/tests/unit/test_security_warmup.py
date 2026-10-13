from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

from app.graph import intent, security_warmup


def test_warmup_preserves_security_decisions():
    messages = [
        "C'est quoi une action ?", "Quel investissement est le meilleur pour moi ?",
        "What is a bond?", "Should I buy this stock with my savings?",
    ]
    before = [intent.security_decision(message) for message in messages]
    assert security_warmup.run_security_warmup()
    assert [intent.security_decision(message) for message in messages] == before


def test_startup_does_not_wait_for_model_and_runs_once(monkeypatch):
    entered, release = Event(), Event()

    def predict(text):
        entered.set()
        assert release.wait(5)

    monkeypatch.setattr(security_warmup, "_thread", None)
    monkeypatch.setattr(security_warmup, "security_model", SimpleNamespace(predict=predict))
    try:
        assert security_warmup.start_security_warmup()
        assert entered.wait(2)
        assert not security_warmup.start_security_warmup()
    finally:
        release.set()
        security_warmup._thread.join(5)


def test_concurrent_warmup_and_request_load_model_once(tmp_path, monkeypatch):
    path = tmp_path / "model.joblib"
    path.touch()
    calls = []
    bundle = {"model": object()}
    monkeypatch.setattr(intent.joblib, "load", lambda path: calls.append(path) or bundle)
    model = intent.LocalIntentModel(path, intent.MissingSecurityArtifact)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: model.load(), range(4)))
    assert all(result is bundle for result in results)
    assert len(calls) == 1


def test_warmup_failure_leaves_missing_model_fail_closed(tmp_path, monkeypatch):
    model = intent.LocalIntentModel(tmp_path / "missing", intent.MissingSecurityArtifact)
    monkeypatch.setattr(security_warmup, "security_model", model)
    assert not security_warmup.run_security_warmup()
    assert model.bundle is None
