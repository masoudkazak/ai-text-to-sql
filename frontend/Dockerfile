FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# ─── builder ────────────────────────────────────────────────────────────────
FROM base AS builder
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ─── production ─────────────────────────────────────────────────────────────
FROM base AS production
ARG APP_UID=10001

RUN groupadd --system appuser \
    && useradd --system --uid "${APP_UID}" --gid appuser --create-home appuser

COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser . .

RUN chmod +x /app/entrypoint.sh

ENV APP_ENV=production \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

USER appuser
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1
ENTRYPOINT ["/app/entrypoint.sh"]

# ─── development ─────────────────────────────────────────────────────────────
FROM production AS development
ENV APP_ENV=development