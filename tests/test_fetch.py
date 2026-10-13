import requests

from transit.ingest.fetch import fetch_feed


class FakeResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.content = content


class FakeSession:
    """Plays back a list of responses or exceptions, one per call."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def get(self, url, headers=None, timeout=None):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def no_sleep(seconds):
    pass


def test_success_on_first_try():
    session = FakeSession([FakeResponse(200, b"payload")])
    result = fetch_feed("http://x", session=session, sleep=no_sleep)
    assert result.ok
    assert result.content == b"payload"
    assert result.attempts == 1
    assert result.error is None


def test_retries_server_error_then_succeeds():
    session = FakeSession([FakeResponse(500), FakeResponse(503), FakeResponse(200, b"ok")])
    result = fetch_feed("http://x", max_retries=3, session=session, sleep=no_sleep)
    assert result.ok
    assert result.attempts == 3
    assert session.calls == 3


def test_gives_up_after_max_retries():
    session = FakeSession([FakeResponse(500)] * 3)
    result = fetch_feed("http://x", max_retries=3, session=session, sleep=no_sleep)
    assert not result.ok
    assert result.content is None
    assert result.status_code == 500
    assert result.attempts == 3
    assert result.error == "HTTP 500"


def test_does_not_retry_404():
    session = FakeSession([FakeResponse(404)])
    result = fetch_feed("http://x", max_retries=3, session=session, sleep=no_sleep)
    assert not result.ok
    assert result.attempts == 1
    assert session.calls == 1


def test_retries_rate_limit_429():
    session = FakeSession([FakeResponse(429), FakeResponse(200, b"ok")])
    result = fetch_feed("http://x", max_retries=3, session=session, sleep=no_sleep)
    assert result.ok
    assert result.attempts == 2


def test_retries_timeout_then_succeeds():
    session = FakeSession([requests.Timeout("slow"), FakeResponse(200, b"ok")])
    result = fetch_feed("http://x", max_retries=3, session=session, sleep=no_sleep)
    assert result.ok
    assert result.attempts == 2


def test_connection_errors_are_reported_not_raised():
    session = FakeSession([requests.ConnectionError("down")] * 3)
    result = fetch_feed("http://x", max_retries=3, session=session, sleep=no_sleep)
    assert not result.ok
    assert result.status_code is None
    assert "ConnectionError" in result.error


def test_backoff_waits_grow_and_skip_the_last_try():
    waits = []
    session = FakeSession([FakeResponse(500)] * 4)
    fetch_feed(
        "http://x",
        max_retries=4,
        backoff_seconds=1.0,
        session=session,
        sleep=waits.append,
    )
    # 4 attempts means 3 waits: 1, 2, 4. No wait after the final attempt.
    assert waits == [1.0, 2.0, 4.0]
