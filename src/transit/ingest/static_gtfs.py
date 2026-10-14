"""Save BART's static schedule (a zip file) once per day.

The realtime feed leaves route_id empty, so line-level metrics need the
static schedule (trips.txt). BART publishes new schedule versions over time
and the permalink only serves the latest one, so we keep a dated copy of
every day. Later we can look up which version was in effect on any date.

Unlike the realtime feed, we check that the download really is a GTFS zip
before saving it. If we saved an HTML error page as "today's schedule", the
job would think today was done and never try again.
"""

import io
import logging
import zipfile
from datetime import datetime, timezone

from transit.ingest.fetch import fetch_feed

FEED_NAME = "bart_gtfs_static"

# The zip is about 1 MB, so give it more time than the small realtime feed.
STATIC_TIMEOUT_SECONDS = 30

log = logging.getLogger("static_gtfs")


def is_valid_gtfs_zip(content):
    """True if content is a zip file that contains trips.txt."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return "trips.txt" in zf.namelist()
    except zipfile.BadZipFile:
        return False


class StaticGtfsJob:
    def __init__(
        self,
        settings,
        store,
        fetch=fetch_feed,
        now=None,
        retry_after_seconds=900,
    ):
        self.settings = settings
        self.store = store
        self.fetch = fetch
        # now can be replaced in tests so we can control the clock.
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.retry_after_seconds = retry_after_seconds
        self.last_attempt = None

    def run_if_due(self):
        """Save today's schedule if we do not have it yet.

        Returns one of: already_saved, waiting_to_retry, saved, failed, invalid.
        """
        current = self.now()

        if self.store.exists_for_day(FEED_NAME, current):
            return "already_saved"

        # After a failure, wait before trying again so we do not hammer BART
        # once a minute for a file we only need once a day.
        if self.last_attempt is not None:
            seconds_since = (current - self.last_attempt).total_seconds()
            if seconds_since < self.retry_after_seconds:
                return "waiting_to_retry"

        self.last_attempt = current
        result = self.fetch(
            self.settings.bart_static_gtfs_url,
            timeout_seconds=STATIC_TIMEOUT_SECONDS,
            max_retries=self.settings.max_retries,
            user_agent=self.settings.user_agent,
        )

        if not result.ok:
            log.error(
                "static schedule fetch failed after %d attempts: %s",
                result.attempts,
                result.error,
            )
            return "failed"

        if not is_valid_gtfs_zip(result.content):
            log.error(
                "static schedule download was not a valid GTFS zip (%d bytes), "
                "will retry later",
                len(result.content),
            )
            return "invalid"

        saved = self.store.save(
            FEED_NAME, result.fetched_at, result.content, extension=".zip"
        )
        log.info("saved static schedule %s (%d bytes)", saved.path, saved.size_bytes)
        return "saved"
