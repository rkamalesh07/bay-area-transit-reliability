"""Helpers for building SYNTHETIC GTFS-Realtime payloads for tests.

Everything built here is made up. It is not real BART data. It exists so we
can test the parser on exact, known inputs.
"""

from google.transit import gtfs_realtime_pb2


def build_feed(trips, timestamp=1760300000):
    """Build feed bytes.

    trips is a list of dicts like:
        {
          "id": "1",
          "trip_id": "t1",
          "route_id": "01",
          "direction_id": 0,
          "stops": [
              {"stop_id": "MONT", "arrival_delay": 60, "departure_delay": 70},
          ],
        }
    Any key you leave out is left unset in the feed.
    """
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = timestamp

    for trip in trips:
        entity = feed.entity.add()
        entity.id = trip["id"]
        update = entity.trip_update

        if "trip_id" in trip:
            update.trip.trip_id = trip["trip_id"]
        if "route_id" in trip:
            update.trip.route_id = trip["route_id"]
        if "direction_id" in trip:
            update.trip.direction_id = trip["direction_id"]
        if "start_date" in trip:
            update.trip.start_date = trip["start_date"]
        if "schedule_relationship" in trip:
            update.trip.schedule_relationship = trip["schedule_relationship"]

        for stop in trip.get("stops", []):
            stu = update.stop_time_update.add()
            if "stop_id" in stop:
                stu.stop_id = stop["stop_id"]
            if "stop_sequence" in stop:
                stu.stop_sequence = stop["stop_sequence"]
            if "arrival_delay" in stop:
                stu.arrival.delay = stop["arrival_delay"]
            if "arrival_time" in stop:
                stu.arrival.time = stop["arrival_time"]
            if "departure_delay" in stop:
                stu.departure.delay = stop["departure_delay"]
            if "departure_time" in stop:
                stu.departure.time = stop["departure_time"]

    return feed.SerializeToString()


def build_alert_only_feed():
    """A feed whose only entity is an alert, not a trip update."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1760300000
    entity = feed.entity.add()
    entity.id = "alert1"
    entity.alert.header_text.translation.add().text = "synthetic alert"
    return feed.SerializeToString()
