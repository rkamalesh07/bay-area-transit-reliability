# Deploying the collector to Railway

This runs the collector all day in its own Railway project and keeps the raw
files on a volume. The repo already has the Dockerfile. You do the clicking.

Before you start: the workspace already has a Compute usage limit (alert at
$5, hard limit at $10). A new service in the same workspace counts toward it.

## 1. Create the service

1. In Railway, create a new project (keep it separate from SwingFactr) and
   choose Deploy from GitHub repo. Pick bay-area-transit-reliability. If the
   repo is not listed, give Railway access to it in the GitHub app settings.
2. Railway builds with the Dockerfile on its own when it finds one at the
   repo root.
3. The first deploy starts before you set variables and a volume. That is
   fine. Its files sit on a temporary disk and are lost on redeploy. Do steps
   2 to 4 right away.

## 2. Variables (service, Variables tab)

```
RAW_DATA_DIR=/data/raw
USER_AGENT=bay-area-transit-reliability/0.1 (student project; contact: your-email@example.com)
```

Leave everything else at its default (poll every 60 seconds). The collector
has no secrets, so do not add any.

## 3. Volume

Create a volume (Command Palette with Cmd+K, or right click on the project
canvas), connect it to the collector service, and set the mount path to
`/data`.

A volume keeps files across redeploys. Without it, every redeploy erases the
collected data. The image runs as root, which is what Railway volumes expect
because they are mounted as root.

## 4. Service settings

- Restart policy: Always. The default is On Failure with a limit of 10
  restarts, after which a crashing collector stays down.
- Settings, Deploy, Replica Limits: set memory to 512 MB for now. A limit set
  too low makes the service crash, so we tighten it after measuring.

Redeploy after changing these if Railway does not do it for you.

## 5. Check that it works

In the service Logs you should see:

- `collector started, polling https://api.bart.gov/... every 60 seconds, saving to /data/raw`
- `saved /data/raw/bart_trip_updates/... (N bytes, N stop predictions, attempts=1)` once a minute
- `saved static schedule /data/raw/bart_gtfs_static/...` once per day, on the first start of that day

Then open the volume metrics and confirm the usage grows.

## 6. After one day

- Memory graph: write down the real average and peak. Set the replica limit a
  bit above the peak.
- Usage page: note what this service added to the bill. Only measured numbers
  go in METRICS.md.

## Notes

- Expect a short gap in polling on every redeploy. Missed polls cannot be
  recovered. The docs do not say how long the gap is.
- Logs are not an archive. Uptime in METRICS.md is computed from the saved
  files, not from the logs.
- The image was not built locally before the first Railway build. If the
  build fails, copy the build log.
- The raw files live on the volume only for now. Copying them to S3 is the
  next step, so they can be analyzed from a laptop.
