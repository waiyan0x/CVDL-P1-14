FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HUB_OFFLINE=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics \
    PADDLE_PDX_CACHE_HOME=/tmp/paddle-runtime \
    EDS_PADDLE_PYTHON=/opt/paddle/bin/python \
    EDS_TORCH_THREADS=2 \
    EDS_MAX_VIDEO_BYTES=30000000

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && apt-get clean \
    && useradd --uid 10001 --create-home reader

WORKDIR /app

COPY requirements-app.txt ./
RUN python -m pip install --no-cache-dir --no-compile --index-url https://download.pytorch.org/whl/cpu \
        torch==2.9.0 torchvision==0.24.0 \
    && python -m pip install --no-cache-dir --no-compile -r requirements-app.txt transformers==4.57.1 \
    && python -m venv /opt/paddle \
    && /opt/paddle/bin/pip install --no-cache-dir --no-compile paddlepaddle==3.2.2 paddleocr==3.3.2

RUN install -d -o reader -g reader .runtime/uploads .runtime/logs
USER reader

EXPOSE 8080
HEALTHCHECK --start-period=120s --interval=30s --timeout=5s \
    CMD python -c 'import json, os, urllib.request; url = "http://127.0.0.1:" + os.environ.get("PORT", "8080") + "/api/health"; status = json.load(urllib.request.urlopen(url, timeout=3)); assert status["ready"] and set(status["backends"]) == {"easyocr", "paddleocr", "trocr"}'
CMD ["sh", "-c", "exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port \"${PORT:-8080}\" --workers 1"]

FROM runtime AS deployment
COPY backend ./backend
COPY frontend ./frontend
COPY data ./data
COPY models ./models
COPY evaluation ./evaluation
COPY .cache ./.cache
