"""Save raw payloads to disk exactly as received.

Why raw and untouched? If we find a bug in our parser later, we can fix it
and re-run on the original bytes. If we had only saved parsed rows, the
original information would be gone.

Files are laid out by feed name and date:
    data/raw/bart_trip_updates/2026/10/12/20261012T213045Z.pb
"""

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SavedFile:
    path: str
    size_bytes: int
    sha256: str  # fingerprint of the content, used later to spot duplicates


class LocalRawStore:
    def __init__(self, base_dir):
        self.base_dir = base_dir

    def save(self, feed_name, fetched_at, content):
        """Write content to disk and return a SavedFile.

        fetched_at must be a timezone-aware UTC datetime.
        """
        folder = os.path.join(
            self.base_dir,
            feed_name,
            fetched_at.strftime("%Y"),
            fetched_at.strftime("%m"),
            fetched_at.strftime("%d"),
        )
        os.makedirs(folder, exist_ok=True)

        stamp = fetched_at.strftime("%Y%m%dT%H%M%SZ")
        path = os.path.join(folder, stamp + ".pb")

        # Never overwrite an existing file. If two saves land in the same
        # second, add a counter to the name.
        counter = 1
        while os.path.exists(path):
            path = os.path.join(folder, stamp + "_" + str(counter) + ".pb")
            counter += 1

        # Write to a temporary file first, then rename. A rename is a single
        # step, so a crash in the middle cannot leave a half-written .pb file.
        temp_path = path + ".tmp"
        with open(temp_path, "wb") as f:
            f.write(content)
        os.replace(temp_path, path)

        return SavedFile(
            path=path,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
