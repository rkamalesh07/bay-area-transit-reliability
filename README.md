# Bay Area Transit Reliability Tracker

A data pipeline that collects BART real-time trip updates, stores them in
layers (raw, cleaned, metrics), and will train a model that predicts delays.

Status: Phase 2 (deploying the collector). Work in progress.

## Data source

BART GTFS-Realtime trip updates. No API key is needed. Usage follows the
[BART Developer License Agreement](https://www.bart.gov/schedules/developers/developer-license-agreement).
This project is not affiliated with BART and does not use BART logos.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env     # then edit USER_AGENT with your contact email
```

## Run the tests

```
pytest
```

## Run the collector locally

```
PYTHONPATH=src python -m transit.ingest.collector
```

Raw payloads are saved under `data/raw/` (ignored by git).

## Capture a real sample for the tests

```
mkdir -p tests/fixtures
curl -o tests/fixtures/real_bart_sample.pb https://api.bart.gov/gtfsrt/tripupdate.aspx
PYTHONPATH=src python scripts/inspect_feed.py tests/fixtures/real_bart_sample.pb
```

## Limitations (so far)

- Trip updates are predictions, not observed arrivals. Any "delay" label built
  from them is an approximation.
- Not yet measured: collection uptime, data volume, model performance.
  See METRICS.md.

## Deploy

The collector runs as a Docker container on Railway with a volume for the raw
files. Step by step instructions are in [docs/deploy.md](docs/deploy.md).
Besides the realtime feed, the collector saves BART's static schedule zip once
a day, because the realtime feed leaves route_id empty.
