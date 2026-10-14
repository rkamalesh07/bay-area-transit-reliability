"""Save raw payloads to disk exactly as received.

Why raw and untouched? If we find a bug in our parser later, we can fix it
and re-run on the original bytes. If we had only saved parsed rows, the
original information would be gone.

Files are laid out by feed name and UTC date:
    data/raw/bart_trip_updates/2026/10/12/20261012T213045Z.pb
    data/raw/bart_gtfs_static/2026/10/12/20261012T213100Z.zip
"""

import hashlib
import os
from dataclasses import dataclass


@dataclass
class SavedFile:
    path: str
    size_bytes: int
    sha256: str  # fingerprint of the content, used later to spot duplicates


class LocalRawStore:
    def __init__(self, base_dir):
        self.base_dir = base_dir

    def _folder(self, feed_name, when):
        return os.path.join(
            self.base_dir,
            feed_name,
            when.strftime("%Y"),
            when.strftime("%m"),
            when.strftime("%d"),
        )

    def save(self, feed_name, fetched_at, content, extension=".pb"):
        """Write content to disk and return a SavedFile.

        fetched_at must be a timezone-aware UTC datetime.
        """
        folder = self._folder(feed_name, fetched_at)
        os.makedirs(folder, exist_ok=True)

        stamp = fetched_at.strftime("%Y%m%dT%H%M%SZ")
        path = os.path.join(folder, stamp + extension)

        # Never overwrite an existing file. If two saves land in the same
        # second, add a counter to the name.
        counter = 1
        while os.path.exists(path):
            path = os.path.join(folder, stamp + "_" + str(counter) + extension)
            counter += 1

        # Write to a temporary file first, then rename. A rename is a single
        # step, so a crash in the middle cannot leave a half-written file.
        temp_path = path + ".tmp"
        with open(temp_path, "wb") as f:
            f.write(content)
        os.replace(temp_path, path)

        return SavedFile(
            path=path,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def exists_for_day(self, feed_name, when):
        """True if at least one finished file was saved for this feed on the
        UTC day of `when`. Half-written .tmp files do not count."""
        folder = self._folder(feed_name, when)
        if not os.path.isdir(folder):
            return False
        for name in os.listdir(folder):
            if not name.endswith(".tmp"):
                return True
        return False
