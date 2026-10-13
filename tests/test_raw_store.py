import hashlib
import os
from datetime import datetime, timezone

from transit.ingest.raw_store import LocalRawStore

WHEN = datetime(2026, 10, 12, 21, 30, 45, tzinfo=timezone.utc)


def test_saves_bytes_untouched(tmp_path):
    store = LocalRawStore(str(tmp_path))
    content = b"\x00\x01binary\xff"
    saved = store.save("feed", WHEN, content)

    with open(saved.path, "rb") as f:
        assert f.read() == content
    assert saved.size_bytes == len(content)
    assert saved.sha256 == hashlib.sha256(content).hexdigest()


def test_path_layout_uses_feed_and_date(tmp_path):
    store = LocalRawStore(str(tmp_path))
    saved = store.save("feed", WHEN, b"x")
    expected = os.path.join(
        str(tmp_path), "feed", "2026", "10", "12", "20261012T213045Z.pb"
    )
    assert saved.path == expected


def test_same_second_does_not_overwrite(tmp_path):
    store = LocalRawStore(str(tmp_path))
    first = store.save("feed", WHEN, b"first")
    second = store.save("feed", WHEN, b"second")

    assert first.path != second.path
    with open(first.path, "rb") as f:
        assert f.read() == b"first"
    with open(second.path, "rb") as f:
        assert f.read() == b"second"


def test_no_temp_files_left_behind(tmp_path):
    store = LocalRawStore(str(tmp_path))
    store.save("feed", WHEN, b"x")
    for _, _, files in os.walk(str(tmp_path)):
        assert not any(name.endswith(".tmp") for name in files)


def test_empty_content_is_still_saved(tmp_path):
    store = LocalRawStore(str(tmp_path))
    saved = store.save("feed", WHEN, b"")
    assert saved.size_bytes == 0
    assert os.path.exists(saved.path)
