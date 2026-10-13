"""Settings for the collector.

All settings come from environment variables so that secrets and
deployment-specific values never live in the code. For local work we
load them from a .env file (see .env.example).
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bart_tripupdates_url: str
    poll_interval_seconds: int
    request_timeout_seconds: int
    max_retries: int
    raw_data_dir: str
    user_agent: str


def load_settings():
    """Read settings from the environment, using safe defaults."""
    load_dotenv()  # does nothing if there is no .env file

    return Settings(
        bart_tripupdates_url=os.getenv(
            "BART_TRIPUPDATES_URL", "https://api.bart.gov/gtfsrt/tripupdate.aspx"
        ),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        raw_data_dir=os.getenv("RAW_DATA_DIR", "data/raw"),
        user_agent=os.getenv(
            "USER_AGENT",
            "bay-area-transit-reliability/0.1 (student project)",
        ),
    )
