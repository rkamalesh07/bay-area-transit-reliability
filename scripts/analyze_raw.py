"""Measure what is in data/raw. Read-only: it never changes your data.

Usage (from the repo root):
    python scripts/analyze_raw.py

Everything printed here is computed from the saved files, so these are the
numbers that are allowed to go into METRICS.md.
"""

import collections
import glob
import hashlib
import os
import statistics
import sys
from datetime import datetime, timezone

sys.path.insert(0, "src")
from transit.parse.trip_updates import ParseError, StopTimeRow, parse_trip_updates


def main():
    paths = sorted(glob.glob("data/raw/bart_trip_updates/*/*/*/*.pb"))
    if not paths:
        print("no files found under data/raw/bart_trip_updates (run from the repo root)")
        return

    fields = list(StopTimeRow.__dataclass_fields__)
    filled = collections.Counter()
    total_rows = 0
    hashes = set()
    sizes = []
    row_counts = []
    lags = []
    fetch_times = []
    feed_stamps = []
    parse_failures = 0
    trip_rel = collections.Counter()
    stop_rel = collections.Counter()
    routes = collections.Counter()
    trips = set()
    stops = set()
    delays = []

    for path in paths:
        with open(path, "rb") as f:
            content = f.read()
        sizes.append(len(content))
        hashes.add(hashlib.sha256(content).hexdigest())

        name = os.path.basename(path)
        fetched = datetime.strptime(name[:15], "%Y%m%dT%H%M%S").replace(
            tzinfo=timezone.utc
        )
        fetch_times.append(fetched)

        try:
            rows = parse_trip_updates(content)
        except ParseError:
            parse_failures += 1
            feed_stamps.append(None)
            continue

        row_counts.append(len(rows))
        feed_stamps.append(rows[0].feed_timestamp if rows else None)
        if rows and rows[0].feed_timestamp is not None:
            lags.append(fetched.timestamp() - rows[0].feed_timestamp)

        for r in rows:
            total_rows += 1
            for field_name in fields:
                if getattr(r, field_name) is not None:
                    filled[field_name] += 1
            trip_rel[r.trip_schedule_relationship] += 1
            stop_rel[r.stop_schedule_relationship] += 1
            routes[r.route_id] += 1
            trips.add(r.trip_id)
            stops.add(r.stop_id)
            if r.arrival_delay is not None:
                delays.append(r.arrival_delay)

    window = (fetch_times[-1] - fetch_times[0]).total_seconds()
    gaps = [(b - a).total_seconds() for a, b in zip(fetch_times, fetch_times[1:])]
    same_stamp = sum(
        1
        for a, b in zip(feed_stamps, feed_stamps[1:])
        if a is not None and a == b
    )

    print("FILES")
    print("  files:", len(paths), "| parse failures:", parse_failures)
    print("  first:", fetch_times[0], "| last:", fetch_times[-1])
    print("  window seconds:", int(window), "| expected polls at 60s:", int(window // 60) + 1)
    if gaps:
        print("  gaps over 90s:", sum(1 for g in gaps if g > 90), "of", len(gaps),
              "| largest gap minutes:", round(max(gaps) / 60, 1))
    print("  bytes total:", sum(sizes), "| min:", min(sizes), "| max:", max(sizes),
          "| mean:", int(statistics.mean(sizes)))
    print("  distinct payloads (sha256):", len(hashes))
    print("  polls whose feed timestamp equals the previous poll:", same_stamp)
    if lags:
        print("  fetch time minus feed timestamp, seconds (min/median/max):",
              int(min(lags)), int(statistics.median(lags)), int(max(lags)))

    print()
    print("ROWS")
    print("  total:", total_rows)
    if row_counts:
        print("  per file min/median/max:", min(row_counts),
              int(statistics.median(row_counts)), max(row_counts))
    print("  distinct trip_ids:", len(trips), "| distinct stop_ids:", len(stops))

    print()
    print("FIELD FILL RATES")
    for field_name in fields:
        pct = 100 * filled[field_name] / total_rows if total_rows else 0
        print("  %-28s %8d of %d (%.1f%%)" % (field_name, filled[field_name], total_rows, pct))

    print()
    print("VALUES")
    print("  trip_schedule_relationship:", dict(trip_rel))
    print("  stop_schedule_relationship:", dict(stop_rel))
    print("  rows per route_id:", sorted((str(k), v) for k, v in routes.items()))
    if delays:
        print("  arrival_delay seconds min/median/max:", min(delays),
              int(statistics.median(delays)), max(delays))
        print("  share arrival_delay == 0:", round(sum(1 for d in delays if d == 0) / len(delays), 3))
        print("  share arrival_delay >= 300:", round(sum(1 for d in delays if d >= 300) / len(delays), 4))


if __name__ == "__main__":
    main()
