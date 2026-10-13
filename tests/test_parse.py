import os

import pytest

from helpers import build_alert_only_feed, build_feed
from transit.parse.trip_updates import ParseError, parse_trip_updates


def test_parses_delays_and_ids():
    content = build_feed(
        [
            {
                "id": "1",
                "trip_id": "t1",
                "route_id": "01",
                "direction_id": 1,
                "start_date": "20261012",
                "stops": [
                    {
                        "stop_id": "MONT",
                        "stop_sequence": 3,
                        "arrival_delay": 60,
                        "arrival_time": 1760300600,
                        "departure_delay": 75,
                        "departure_time": 1760300615,
                    }
                ],
            }
        ]
    )
    rows = parse_trip_updates(content)

    assert len(rows) == 1
    row = rows[0]
    assert row.feed_timestamp == 1760300000
    assert row.trip_id == "t1"
    assert row.route_id == "01"
    assert row.direction_id == 1
    assert row.stop_id == "MONT"
    assert row.arrival_delay == 60
    assert row.departure_delay == 75
    assert row.arrival_time == 1760300600


def test_one_row_per_stop_prediction():
    content = build_feed(
        [
            {
                "id": "1",
                "trip_id": "t1",
                "stops": [
                    {"stop_id": "A", "arrival_delay": 0},
                    {"stop_id": "B", "arrival_delay": 30},
                    {"stop_id": "C", "arrival_delay": 90},
                ],
            },
            {"id": "2", "trip_id": "t2", "stops": [{"stop_id": "A"}]},
        ]
    )
    rows = parse_trip_updates(content)
    assert len(rows) == 4
    assert [r.stop_id for r in rows if r.trip_id == "t1"] == ["A", "B", "C"]


def test_missing_fields_are_none_not_zero():
    content = build_feed(
        [{"id": "1", "trip_id": "t1", "stops": [{"stop_id": "A"}]}]
    )
    row = parse_trip_updates(content)[0]
    assert row.arrival_delay is None
    assert row.departure_delay is None
    assert row.route_id is None
    assert row.direction_id is None


def test_zero_delay_is_kept_as_zero():
    # A real "on time" prediction must stay 0 and not turn into None.
    content = build_feed(
        [{"id": "1", "trip_id": "t1", "stops": [{"stop_id": "A", "arrival_delay": 0}]}]
    )
    row = parse_trip_updates(content)[0]
    assert row.arrival_delay == 0


def test_negative_delay_means_early():
    content = build_feed(
        [{"id": "1", "trip_id": "t1", "stops": [{"stop_id": "A", "arrival_delay": -45}]}]
    )
    assert parse_trip_updates(content)[0].arrival_delay == -45


def test_canceled_trip_relationship_is_captured():
    content = build_feed(
        [
            {
                "id": "1",
                "trip_id": "t1",
                "schedule_relationship": 3,  # CANCELED
                "stops": [{"stop_id": "A"}],
            }
        ]
    )
    assert parse_trip_updates(content)[0].trip_schedule_relationship == 3


def test_trip_with_no_stop_updates_gives_no_rows():
    content = build_feed([{"id": "1", "trip_id": "t1", "stops": []}])
    assert parse_trip_updates(content) == []


def test_feed_with_no_entities_gives_empty_list():
    assert parse_trip_updates(build_feed([])) == []


def test_alert_entities_are_skipped():
    assert parse_trip_updates(build_alert_only_feed()) == []


def test_corrupt_bytes_raise_parse_error():
    with pytest.raises(ParseError):
        parse_trip_updates(b"this is definitely not protobuf \xff\xfe\x00")


def test_empty_bytes_raise_parse_error():
    # An empty body is not a valid feed (the header is required).
    with pytest.raises(ParseError):
        parse_trip_updates(b"")


def test_html_error_page_raises_parse_error():
    # Servers sometimes return an HTML error page with status 200.
    with pytest.raises(ParseError):
        parse_trip_updates(b"<html><body>Service unavailable</body></html>")


REAL_SAMPLE = os.path.join(
    os.path.dirname(__file__), "fixtures", "real_bart_sample.pb"
)


@pytest.mark.skipif(
    not os.path.exists(REAL_SAMPLE),
    reason="no real BART sample captured yet (see README)",
)
def test_real_sample_parses():
    with open(REAL_SAMPLE, "rb") as f:
        rows = parse_trip_updates(f.read())
    assert len(rows) > 0
    assert rows[0].feed_timestamp is not None
