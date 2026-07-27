import pytest

from job_monitor.notify import telegram


def make_job():
    return {"title": "Senior Product Designer", "location": "Remote", "url": "https://example.com/job"}


class FakeResponse:
    def __init__(self, json_data=None, json_error=None, raise_error=None):
        self._json_data = json_data
        self._json_error = json_error
        self._raise_error = raise_error

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._json_data

    def raise_for_status(self):
        if self._raise_error:
            raise self._raise_error


@pytest.fixture(autouse=True)
def telegram_creds(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:FAKE-TEST-TOKEN")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")


def test_send_fails_gracefully_when_token_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    called = []
    monkeypatch.setattr(telegram.requests, "post", lambda *a, **k: called.append(1))

    success, err = telegram.send("Acme", make_job(), "Product Design/UX", "2026-07-27 10:00 AM")

    assert success is False
    assert "TELEGRAM_BOT_TOKEN" in err
    assert called == []  # never even attempted the network call


def test_send_success(monkeypatch):
    monkeypatch.setattr(telegram.requests, "post", lambda *a, **k: FakeResponse(json_data={"ok": True}))

    success, err = telegram.send("Acme", make_job(), "Product Design/UX", "2026-07-27 10:00 AM")

    assert success is True
    assert err is None


def test_send_surfaces_real_telegram_error_description(monkeypatch):
    resp = FakeResponse(json_data={"ok": False, "description": "Bad Request: chat not found"})
    monkeypatch.setattr(telegram.requests, "post", lambda *a, **k: resp)

    success, err = telegram.send("Acme", make_job(), "Product Design/UX", "2026-07-27 10:00 AM")

    assert success is False
    assert err == "Bad Request: chat not found"


def test_send_redacts_token_from_transport_level_errors(monkeypatch):
    token = "123456:FAKE-TEST-TOKEN"

    class BoomOnJson(FakeResponse):
        def json(self):
            raise ValueError("not json")

        def raise_for_status(self):
            raise RuntimeError(f"400 Client Error: Bad Request for url: https://api.telegram.org/bot{token}/sendMessage")

    monkeypatch.setattr(telegram.requests, "post", lambda *a, **k: BoomOnJson())

    success, err = telegram.send("Acme", make_job(), "Product Design/UX", "2026-07-27 10:00 AM")

    assert success is False
    assert token not in err
    assert "<redacted>" in err
