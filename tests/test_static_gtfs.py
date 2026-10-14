import io
import os
import zipfile
from datetime import datetime, timedelta, timezone

from transit.config import Settings
from transit.ingest.fetch import FetchResult
from transit.ingest.raw_store import LocalRawStore
from transit.ingest.static_gtfs import FEED_NAME, StaticGtfsJob, is_valid_gtfs_zip

START = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)


def make_zip(names=("trips.txt", "routes.txt")):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name in names:
            zf.writestr(name, "a,b\n1,2\n")
    return buffer.getvalue()


class Clock:
    """A fake clock that only moves when the test says so."""

    def __init__(self):
        self.current = START

    def now(self):
        return self.current

    def advance(self, seconds):
        self.current = self.current + timedelta(seconds=seconds)


class FakeFetch:
    """Plays back outcomes in order. An outcome is bytes (a good download)
    or None (a failed download)."""

    def __init__(self, clock, outcomes):
        self.clock = clock
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self, url, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if outcome is None:
            return FetchResult(
                url=url,
                fetched_at=self.clock.now(),
                ok=False,
                status_code=500,
                content=None,
                attempts=3,
                error="HTTP 500",
            )
        return FetchResult(
            url=url,
            fetched_at=self.clock.now(),
            ok=True,
            status_code=200,
            content=outcome,
            attempts=1,
            error=None,
        )


def make_job(tmp_path, outcomes):
    clock = Clock()
    settings = Settings(
        bart_tripupdates_url="http://example.test/rt",
        poll_interval_seconds=60,
        request_timeout_seconds=1,
        max_retries=1,
        raw_data_dir=str(tmp_path),
        user_agent="test",
    )
    store = LocalRawStore(str(tmp_path))
    fetch = FakeFetch(clock, outcomes)
    job = StaticGtfsJob(settings, store, fetch=fetch, now=clock.now)
    return job, store, fetch, clock


def count_zip_files(folder):
    total = 0
    for _, _, files in os.walk(str(folder)):
        total += sum(1 for name in files if name.endswith(".zip"))
    return total


def test_is_valid_gtfs_zip_cases():
    assert is_valid_gtfs_zip(make_zip()) is True
    assert is_valid_gtfs_zip(make_zip(names=("routes.txt",))) is False  # no trips.txt
    assert is_valid_gtfs_zip(b"<html>301 Moved Permanently</html>") is False
    assert is_valid_gtfs_zip(b"") is False


def test_saves_valid_zip_when_none_today(tmp_path):
    job, store, fetch, clock = make_job(tmp_path, [make_zip()])
    assert job.run_if_due() == "saved"
    assert store.exists_for_day(FEED_NAME, clock.now())
    assert count_zip_files(tmp_path) == 1


def test_does_not_fetch_again_the_same_day(tmp_path):
    job, store, fetch, clock = make_job(tmp_path, [make_zip(), make_zip()])
    assert job.run_if_due() == "saved"
    clock.advance(3600)
    assert job.run_if_due() == "already_saved"
    assert fetch.calls == 1
    assert count_zip_files(tmp_path) == 1


def test_html_instead_of_zip_is_not_saved(tmp_path):
    job, store, fetch, clock = make_job(tmp_path, [b"<html>oops</html>"])
    assert job.run_if_due() == "invalid"
    assert count_zip_files(tmp_path) == 0
    assert not store.exists_for_day(FEED_NAME, clock.now())


def test_zip_without_trips_is_not_saved(tmp_path):
    job, store, fetch, clock = make_job(tmp_path, [make_zip(names=("routes.txt",))])
    assert job.run_if_due() == "invalid"
    assert count_zip_files(tmp_path) == 0


def test_failed_fetch_saves_nothing(tmp_path):
    job, store, fetch, clock = make_job(tmp_path, [None])
    assert job.run_if_due() == "failed"
    assert count_zip_files(tmp_path) == 0


def test_waits_before_retrying_after_a_failure(tmp_path):
    job, store, fetch, clock = make_job(tmp_path, [None, make_zip()])
    assert job.run_if_due() == "failed"

    clock.advance(60)
    assert job.run_if_due() == "waiting_to_retry"
    assert fetch.calls == 1  # did not hit BART again after one minute

    clock.advance(900)
    assert job.run_if_due() == "saved"
    assert fetch.calls == 2
    assert count_zip_files(tmp_path) == 1


def test_fetches_again_the_next_day(tmp_path):
    job, store, fetch, clock = make_job(tmp_path, [make_zip(), make_zip()])
    assert job.run_if_due() == "saved"
    clock.advance(24 * 3600)
    assert job.run_if_due() == "saved"
    assert count_zip_files(tmp_path) == 2
