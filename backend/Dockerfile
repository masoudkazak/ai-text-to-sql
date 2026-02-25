FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# ─── builder ────────────────────────────────────────────────────────────────
FROM base AS builder
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ─── production ─────────────────────────────────────────────────────────────
FROM base AS production
ARG APP_UID=10001

RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system appuser \
    && useradd --system --uid "${APP_UID}" --gid appuser --create-home appuser

COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser . .

RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app

ENV APP_ENV=production \
    RUN_SEED_DATA=0

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
ENTRYPOINT ["/app/entrypoint.sh"]

# ─── development ─────────────────────────────────────────────────────────────
FROM base AS development

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/logs

ENV APP_ENV=development \
    RUN_SEED_DATA=1

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
