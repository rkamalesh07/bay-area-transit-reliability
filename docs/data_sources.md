# Data sources

## BART GTFS-Realtime trip updates (used in v1)

- URL: https://api.bart.gov/gtfsrt/tripupdate.aspx (the old http address redirects to https)
- No API key needed.
- Terms: BART Developer License Agreement, read 2026-10-12. It grants limited,
  revocable rights, forbids BART trademarks and logos, provides the data as is,
  and lets BART stop providing it at any time. BART also asks for a link back.
- No rate limit is published. This project polls once per minute and sends a
  descriptive User-Agent.
- BART's own notes: trip_ids for Antioch and Pittsburg Center (600 range) do not
  match the static schedule, and the Oakland Airport Connector has no realtime
  arrival data.

## BART static GTFS schedule (needed for route_id)

- Permalink: https://www.bart.gov/dev/schedules/google_transit.zip
- BART says to check the permalink regularly for the latest version, and it also
  lists dated archive files. Schedules change, so the collector saves a copy of
  the zip every day with its date.

## What BART fills in (29,745 rows, laptop run on 2026-10-12)

| Field | Filled |
|---|---|
| feed_timestamp, entity_id, trip_id, stop_id | 100% |
| trip_schedule_relationship | 100% (3 rows are canceled trips) |
| arrival_delay, arrival_time, departure_delay, departure_time | 100% |
| route_id, direction_id, start_date, stop_sequence | 0% |
| stop_schedule_relationship | 0% |

## Caveats

- Trip updates are predictions, not observed arrivals. A delay label built from
  them is an approximation.
- route_id is empty in the realtime feed, so line-level metrics need a join to
  the static schedule by trip_id.
- No negative delays appeared in this sample, so early arrivals may not be reported.

## 511 SF Bay (not used in v1)

Needs a free token. The default limit is 60 requests per hour per token.
