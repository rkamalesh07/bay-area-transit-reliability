# METRICS

Only numbers that were actually measured go in this file.
Anything not measured yet says "not measured yet".

## Collection: local laptop test run (2026-10-12, NOT the deployed collector)

Measured with scripts/analyze_raw.py on the saved files, plus the collector log.

| Metric | Value |
|---|---|
| Run window | 2026-10-13 00:58:37 UTC to 05:49:25 UTC (4.85 hours) |
| Raw files saved | 34 |
| Polls expected at 60 s in the window | 291 |
| Share of expected polls saved | 11.7% (laptop slept or lost its connection) |
| Gaps longer than 90 s | 11 of 33 |
| Largest gap | 88.3 minutes |
| Failed fetch rounds (from log) | 6, all DNS errors on the laptop |
| Polls that failed, then succeeded on retry (from log) | 1 |
| Raw bytes total | 1,072,102 |
| Raw bytes per file (min / mean / max) | 18,888 / 31,532 / 40,105 |
| Parse failures | 0 |
| Consecutive polls with the same feed timestamp | 0 |
| Seconds between feed timestamp and fetch | 0 to 1 |

## Collection: deployed collector

| Metric | Value |
|---|---|
| Collector start date | not measured yet |
| Raw files collected | not measured yet |
| Collection uptime | not measured yet |
| Failed fetches | not measured yet |

## Data shape (same laptop run, counted by row)

Rows repeat the same predictions across polls, so these shares are by row, not by trip.

| Metric | Value |
|---|---|
| Stop predictions (rows) | 29,745 |
| Rows per file (min / median / max) | 515 / 1,070 / 1,120 |
| Distinct trip_ids | 235 |
| Distinct stop_ids | 98 |
| Rows for canceled trips | 3 |
| route_id, direction_id, start_date, stop_sequence filled | 0% |
| arrival_delay filled | 100% |
| arrival_delay seconds (min / median / max) | 0 / 0 / 997 |
| Rows with arrival_delay exactly 0 | 85.8% |
| Rows with arrival_delay of 300 s or more | 0.43% |

## Pipeline

| Metric | Value |
|---|---|
| Rows in cleaned table | not measured yet |
| Pipeline runtime | not measured yet |
| Data quality checks implemented | not measured yet |

## Tests

| Metric | Value |
|---|---|
| Tests passing | 31 (pytest) |
| Test data | synthetic payloads built in code, plus one real BART sample |

## Model

| Metric | Value |
|---|---|
| Training data window | not measured yet |
| Model vs naive baseline | not measured yet |
| Calibration check | not measured yet |

## Cost

| Metric | Value |
|---|---|
| Railway cost for the collector | not measured yet |
| AWS cost | not measured yet |
