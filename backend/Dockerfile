FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-core.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements-core.txt

COPY app ./app
RUN mkdir -p /app/uploads

EXPOSE 8000
# This portable image is intentionally fail-closed and does not include the
# GPU/NeMo model runtime. Production scoring uses the frozen private-edge host
# environment documented in docs/WORD_MODEL_INSTALLATION.md.
CMD ["sh", "-c", "uvicorn app.main:app --host 127.0.0.1 --port ${PORT:-8000} --workers 1"]
