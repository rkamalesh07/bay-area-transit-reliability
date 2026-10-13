import logging
import threading
from datetime import datetime, timezone

from helpers import build_feed
from transit.config import Settings
from transit.ingest.collector import run_forever, run_once
from transit.ingest.fetch import FetchResult
from transit.ingest.raw_store import LocalRawStore


def make_settings(tmp_path):
    return Settings(
        bart_tripupdates_url="http://example.test/feed",
        poll_interval_seconds=60,
        request_timeout_seconds=1,
        max_retries=1,
        raw_data_dir=str(tmp_path),
        user_agent="test",
    )


def ok_result(content):
    return FetchResult(
        url="http://example.test/feed",
        fetched_at=datetime.now(timezone.utc),
        ok=True,
        status_code=200,
        content=content,
        attempts=1,
        error=None,
    )


def failed_result():
    return FetchResult(
        url="http://example.test/feed",
        fetched_at=datetime.now(timezone.utc),
        ok=False,
        status_code=500,
        content=None,
        attempts=3,
        error="HTTP 500",
    )


def count_files(folder):
    import os

    total = 0
    for _, _, files in os.walk(str(folder)):
        total += len(files)
    return total


def test_run_once_saves_good_payload(tmp_path):
    settings = make_settings(tmp_path)
    store = LocalRawStore(str(tmp_path))
    payload = build_feed(
        [{"id": "1", "trip_id": "t1", "stops": [{"stop_id": "A", "arrival_delay": 5}]}]
    )

    outcome = run_once(settings, store, fetch=lambda *a, **k: ok_result(payload))

    assert outcome["saved"] is True
    assert outcome["parse_ok"] is True
    assert outcome["row_count"] == 1
    assert count_files(tmp_path) == 1


def test_run_once_failed_fetch_saves_nothing(tmp_path):
    settings = make_settings(tmp_path)
    store = LocalRawStore(str(tmp_path))

    outcome = run_once(settings, store, fetch=lambda *a, **k: failed_result())

    assert outcome["saved"] is False
    assert outcome["error"] == "HTTP 500"
    assert count_files(tmp_path) == 0


def test_garbage_payload_is_saved_but_flagged(tmp_path, caplog):
    settings = make_settings(tmp_path)
    store = LocalRawStore(str(tmp_path))

    with caplog.at_level(logging.WARNING):
        outcome = run_once(
            settings, store, fetch=lambda *a, **k: ok_result(b"<html>oops</html>")
        )

    assert outcome["saved"] is True
    assert outcome["parse_ok"] is False
    assert count_files(tmp_path) == 1
    assert "did not parse" in caplog.text


def test_loop_survives_unexpected_errors(tmp_path):
    settings = make_settings(tmp_path)
    store = LocalRawStore(str(tmp_path))
    calls = {"n": 0}

    def flaky_fetch(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("bug in fetch")
        return ok_result(build_feed([]))

    run_forever(
        settings,
        store,
        threading.Event(),
        fetch=flaky_fetch,
        sleep=lambda seconds: None,
        max_iterations=3,
    )

    assert calls["n"] == 3  # kept going after the crash in round one
    assert count_files(tmp_path) == 2  # rounds two and three saved


def test_loop_stops_when_event_is_set(tmp_path):
    settings = make_settings(tmp_path)
    store = LocalRawStore(str(tmp_path))
    stop = threading.Event()
    stop.set()
    calls = {"n": 0}

    def fetch(*args, **kwargs):
        calls["n"] += 1
        return ok_result(build_feed([]))

    run_forever(settings, store, stop, fetch=fetch, sleep=lambda s: None)
    assert calls["n"] == 0
