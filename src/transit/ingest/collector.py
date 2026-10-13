"""The collector: fetch the feed every minute and save the raw bytes.

The most important rule here is that the loop must never die because of
one bad response. Every failure is logged and the loop keeps going.
"""

import logging
import signal
import threading
import time

from transit.config import load_settings
from transit.ingest.fetch import fetch_feed
from transit.ingest.raw_store import LocalRawStore
from transit.parse.trip_updates import ParseError, parse_trip_updates

FEED_NAME = "bart_trip_updates"

log = logging.getLogger("collector")


def run_once(settings, store, fetch=fetch_feed):
    """Do one collection. Returns a small dict describing what happened,
    which is handy for logging and for tests."""
    result = fetch(
        settings.bart_tripupdates_url,
        timeout_seconds=settings.request_timeout_seconds,
        max_retries=settings.max_retries,
        user_agent=settings.user_agent,
    )

    if not result.ok:
        log.error(
            "fetch failed after %d attempts: %s", result.attempts, result.error
        )
        return {"saved": False, "error": result.error}

    saved = store.save(FEED_NAME, result.fetched_at, result.content)

    # Save first, parse second. We keep the raw bytes even if they turn out
    # to be unreadable, so we can look at them later.
    try:
        rows = parse_trip_updates(result.content)
        parse_ok = True
        row_count = len(rows)
    except ParseError as exc:
        parse_ok = False
        row_count = 0
        log.warning("saved %s but it did not parse: %s", saved.path, exc)

    log.info(
        "saved %s (%d bytes, %d stop predictions, attempts=%d)",
        saved.path,
        saved.size_bytes,
        row_count,
        result.attempts,
    )
    return {
        "saved": True,
        "path": saved.path,
        "size_bytes": saved.size_bytes,
        "sha256": saved.sha256,
        "parse_ok": parse_ok,
        "row_count": row_count,
    }


def run_forever(
    settings,
    store,
    stop_event,
    fetch=fetch_feed,
    sleep=time.sleep,
    max_iterations=None,
):
    """Call run_once on a steady schedule until stop_event is set.

    stop_event is a threading.Event. Railway sends SIGTERM when it stops a
    container, and main() turns that into stop_event.set() so we exit
    cleanly. max_iterations lets tests stop the loop after a few rounds.
    """
    iterations = 0
    while not stop_event.is_set():
        started = time.monotonic()

        try:
            run_once(settings, store, fetch=fetch)
        except Exception:
            # A bug in our own code must not kill the collector either.
            log.exception("unexpected error in run_once, continuing")

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break

        # Sleep for the rest of the interval so the schedule does not drift.
        elapsed = time.monotonic() - started
        wait = max(0, settings.poll_interval_seconds - elapsed)
        sleep(wait)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    store = LocalRawStore(settings.raw_data_dir)

    stop_event = threading.Event()

    def handle_signal(signum, frame):
        log.info("received signal %s, shutting down", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log.info(
        "collector started, polling %s every %d seconds",
        settings.bart_tripupdates_url,
        settings.poll_interval_seconds,
    )
    # Use an Event wait instead of sleep so shutdown is not delayed.
    run_forever(settings, store, stop_event, sleep=stop_event.wait)
    log.info("collector stopped")


if __name__ == "__main__":
    main()
