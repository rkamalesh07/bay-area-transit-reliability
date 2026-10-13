"""Turn a raw GTFS-Realtime trip updates payload into plain rows.

GTFS-Realtime is sent as Protocol Buffers ("protobuf"): a compact binary
format. We cannot read the bytes directly, so we use Google's generated
classes (the gtfs-realtime-bindings package) to decode them.

One feed contains many "entities". Each trip update entity has a trip and a
list of stop_time_updates (predictions for upcoming stops). We flatten that
into one row per (trip, stop) prediction, which is easy to put in a table.

Many fields are optional in the spec. If a field is missing we store None,
not 0, because "no delay reported" and "0 seconds late" mean different things.
"""

from dataclasses import dataclass
from typing import Optional

from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2


class ParseError(Exception):
    """Raised when the payload is not a valid GTFS-Realtime feed."""


@dataclass
class StopTimeRow:
    feed_timestamp: Optional[int]  # when BART generated the feed (unix seconds)
    entity_id: str
    trip_id: Optional[str]
    route_id: Optional[str]
    direction_id: Optional[int]
    start_date: Optional[str]  # YYYYMMDD
    trip_schedule_relationship: Optional[int]  # 0 scheduled, 3 canceled, ...
    stop_sequence: Optional[int]
    stop_id: Optional[str]
    arrival_delay: Optional[int]  # seconds, negative means early
    arrival_time: Optional[int]  # predicted arrival, unix seconds
    departure_delay: Optional[int]
    departure_time: Optional[int]
    stop_schedule_relationship: Optional[int]


def _get(message, field_name):
    """Return the field value, or None if the sender did not set it."""
    if message.HasField(field_name):
        return getattr(message, field_name)
    return None


def parse_trip_updates(content):
    """Decode bytes into a list of StopTimeRow. Raises ParseError if the
    bytes are not a valid feed. A valid feed with no trip updates returns
    an empty list."""
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(content)
    except DecodeError as exc:
        raise ParseError("could not decode payload: " + str(exc))

    # Empty bytes decode "successfully" into an empty message, so decoding
    # alone is not enough. The spec says every real feed has a header, so a
    # missing header means this is not a real feed (for example an empty body).
    if not feed.HasField("header"):
        raise ParseError("payload has no feed header, not a GTFS-Realtime feed")

    feed_timestamp = _get(feed.header, "timestamp")
    rows = []

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue  # this entity is something else, like an alert

        update = entity.trip_update
        trip = update.trip

        for stop_update in update.stop_time_update:
            arrival = stop_update.arrival
            departure = stop_update.departure

            rows.append(
                StopTimeRow(
                    feed_timestamp=feed_timestamp,
                    entity_id=entity.id,
                    trip_id=_get(trip, "trip_id"),
                    route_id=_get(trip, "route_id"),
                    direction_id=_get(trip, "direction_id"),
                    start_date=_get(trip, "start_date"),
                    trip_schedule_relationship=_get(trip, "schedule_relationship"),
                    stop_sequence=_get(stop_update, "stop_sequence"),
                    stop_id=_get(stop_update, "stop_id"),
                    arrival_delay=_get(arrival, "delay"),
                    arrival_time=_get(arrival, "time"),
                    departure_delay=_get(departure, "delay"),
                    departure_time=_get(departure, "time"),
                    stop_schedule_relationship=_get(
                        stop_update, "schedule_relationship"
                    ),
                )
            )

    return rows
