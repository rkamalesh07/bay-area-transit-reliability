"""Print which fields are actually filled in for a saved feed file.

Usage:
    PYTHONPATH=src python scripts/inspect_feed.py path/to/file.pb

GTFS-Realtime says most fields are optional. Before we design tables we
need to know which ones BART really fills in.
"""

import sys

from transit.parse.trip_updates import ParseError, parse_trip_updates


def main():
    if len(sys.argv) != 2:
        print("usage: inspect_feed.py <file.pb>")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        content = f.read()

    try:
        rows = parse_trip_updates(content)
    except ParseError as exc:
        print("could not parse:", exc)
        sys.exit(1)

    print("file size (bytes):", len(content))
    print("stop predictions:", len(rows))
    if not rows:
        return

    print("feed timestamp:", rows[0].feed_timestamp)
    print()
    print("field                         filled   of")
    for field_name in rows[0].__dataclass_fields__:
        filled = sum(1 for r in rows if getattr(r, field_name) is not None)
        print(f"{field_name:<28} {filled:>7} {len(rows):>4}")

    print()
    print("distinct trips:", len({r.trip_id for r in rows}))
    print("distinct routes:", sorted({str(r.route_id) for r in rows}))


if __name__ == "__main__":
    main()
