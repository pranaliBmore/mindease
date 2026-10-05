# MindEase backend - FastAPI + MongoDB (Atlas) + ONNX emotion models.
# Build context is the `backend/` directory (see render.yaml: dockerContext).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# opencv-python-headless still links libglib; nothing else is needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Model weights are no longer pre-fetched at build time (3 sequential downloads,
# up to 120s each worst case, was the slow/unpredictable part of the build).
# They lazy-download on the first real /api/emotion/detect call instead - that one
# request is ~20-30s slower, everything after it is fast since the files are cached
# to local disk for the life of the container.

# Run as a non-root user.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# One worker on purpose: the realtime WebSocket manager keeps state in-process.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips=*"]
