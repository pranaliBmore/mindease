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

# Bake the ONNX model weights into the image at build time. Render's container disk
# is wiped on every redeploy, so without this, the first real /api/emotion/detect
# request after every deploy had to download ~51MB on the spot - on a slow/congested
# connection that stalls or takes long enough to look like the feature is broken.
# A failed download here does not fail the build (see fetch_models.py); the detector
# still lazy-downloads as a fallback at runtime.
RUN python -m scripts.fetch_models

# Run as a non-root user.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# One worker on purpose: the realtime WebSocket manager keeps state in-process.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips=*"]
