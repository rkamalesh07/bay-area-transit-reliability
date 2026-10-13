"""Download a feed from a URL, with retries.

Networks fail. A request can time out, the server can return an error, or
the connection can drop. We retry a few times with a growing wait
(exponential backoff) so that one bad moment does not cost us a data point.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests


@dataclass
class FetchResult:
    url: str
    fetched_at: datetime  # UTC time of the last attempt
    ok: bool  # True only if we got HTTP 200
    status_code: Optional[int]  # None if we never got a response
    content: Optional[bytes]  # the raw payload, only set when ok is True
    attempts: int  # how many tries it took
    error: Optional[str]  # short description if ok is False


def _should_retry(status_code):
    """Retry server errors and rate limiting. Other 4xx errors will not
    fix themselves, so retrying them would just waste requests."""
    return status_code == 429 or status_code >= 500


def fetch_feed(
    url,
    timeout_seconds=10,
    max_retries=3,
    backoff_seconds=1.0,
    user_agent="bay-area-transit-reliability",
    session=None,
    sleep=time.sleep,
):
    """Fetch url and return a FetchResult. This function never raises for
    network problems, it reports them in the result instead.

    session and sleep can be replaced in tests so no real network or
    waiting is needed.
    """
    if session is None:
        session = requests.Session()

    headers = {"User-Agent": user_agent}
    last_error = None
    last_status = None
    attempts = 0

    for attempt in range(1, max_retries + 1):
        attempts = attempt
        try:
            response = session.get(url, headers=headers, timeout=timeout_seconds)
            last_status = response.status_code

            if response.status_code == 200:
                return FetchResult(
                    url=url,
                    fetched_at=datetime.now(timezone.utc),
                    ok=True,
                    status_code=200,
                    content=response.content,
                    attempts=attempts,
                    error=None,
                )

            last_error = "HTTP " + str(response.status_code)
            if not _should_retry(response.status_code):
                break  # no point retrying a 404, for example

        except requests.RequestException as exc:
            # Timeouts and connection errors both land here.
            last_error = type(exc).__name__ + ": " + str(exc)
            last_status = None

        # Wait before the next try: 1s, 2s, 4s, ... (not after the last try)
        if attempt < max_retries:
            sleep(backoff_seconds * (2 ** (attempt - 1)))

    return FetchResult(
        url=url,
        fetched_at=datetime.now(timezone.utc),
        ok=False,
        status_code=last_status,
        content=None,
        attempts=attempts,
        error=last_error,
    )
