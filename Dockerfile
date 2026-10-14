# Small official Python image. "slim" leaves out compilers and extra tools.
FROM python:3.13-slim

# Show logs immediately (Railway reads them from stdout), skip .pyc files,
# and let Python find our code under /app/src.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install dependencies first. Docker caches every step, so this step only
# re-runs when requirements.txt changes, not on every code change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the code.
COPY src ./src

# Settings come from environment variables set in Railway (see docs/deploy.md).
# The volume is attached when the container starts, not while it is built.
CMD ["python", "-m", "transit.ingest.collector"]
