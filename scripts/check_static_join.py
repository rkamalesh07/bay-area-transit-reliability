"""Check whether realtime trip_ids can be joined to a static GTFS zip.

Usage (from the repo root):
    python scripts/check_static_join.py path/to/bart_gtfs.zip

Why this matters: the realtime feed leaves route_id empty, so line-level
metrics need route_id from the static schedule (trips.txt), joined by trip_id.
Read-only: nothing is changed or deleted.
"""

import collections
import csv
import glob
import io
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from transit.parse.trip_updates import ParseError, parse_trip_updates


def read_table(zf, name):
    """Return one GTFS text file as a list of dicts, or None if missing."""
    if name not in zf.namelist():
        return None
    with zf.open(name) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        return list(csv.DictReader(text))


def main():
    if len(sys.argv) != 2:
        print("usage: check_static_join.py <gtfs.zip>")
        sys.exit(1)

    with zipfile.ZipFile(sys.argv[1]) as zf:
        print("files in zip:", sorted(zf.namelist()))
        trips = read_table(zf, "trips.txt")
        routes = read_table(zf, "routes.txt")
        feed_info = read_table(zf, "feed_info.txt")

    if trips is None:
        print("trips.txt not found in the zip")
        sys.exit(1)

    static_by_trip = {}
    for t in trips:
        static_by_trip[t["trip_id"]] = t

    print()
    print("STATIC SCHEDULE")
    print("  trips.txt rows:", len(trips), "| distinct trip_ids:", len(static_by_trip))
    if feed_info:
        print("  feed_info:", feed_info[0])
    if routes:
        for r in routes:
            print(
                "  route",
                r.get("route_id"),
                "|",
                r.get("route_short_name"),
                "|",
                r.get("route_long_name"),
            )

    rows_per_trip = collections.Counter()
    pattern = os.path.join("data", "raw", "bart_trip_updates", "*", "*", "*", "*.pb")
    paths = sorted(glob.glob(pattern))
    for path in paths:
        with open(path, "rb") as f:
            content = f.read()
        try:
            rows = parse_trip_updates(content)
        except ParseError:
            continue
        for r in rows:
            if r.trip_id is not None:
                rows_per_trip[r.trip_id] += 1

    if not rows_per_trip:
        print("no realtime rows found under data/raw (run from the repo root)")
        return

    realtime_ids = set(rows_per_trip)
    matched = realtime_ids & set(static_by_trip)
    unmatched = sorted(realtime_ids - matched)
    rows_total = sum(rows_per_trip.values())
    rows_matched = sum(rows_per_trip[t] for t in matched)

    print()
    print("JOIN RESULT (realtime trip_id found in static trips.txt)")
    print("  raw files read:", len(paths))
    print("  distinct realtime trip_ids:", len(realtime_ids))
    print(
        "  matched trip_ids: %d (%.1f%%)"
        % (len(matched), 100 * len(matched) / len(realtime_ids))
    )
    print(
        "  matched rows: %d of %d (%.1f%%)"
        % (rows_matched, rows_total, 100 * rows_matched / rows_total)
    )
    print("  unmatched examples:", unmatched[:15])

    by_route = collections.Counter()
    by_direction = collections.Counter()
    for t in matched:
        by_route[static_by_trip[t].get("route_id")] += rows_per_trip[t]
        by_direction[static_by_trip[t].get("direction_id")] += rows_per_trip[t]
    print("  matched rows by static route_id:", sorted(by_route.items(), key=str))
    print("  matched rows by static direction_id:", sorted(by_direction.items(), key=str))


if __name__ == "__main__":
    main()
