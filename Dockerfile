# The deployable artifact. One image for every target (Azure Container Apps,
# local docker compose, anything that runs OCI images). Databricks Apps deploys
# from source instead — see deploy/databricks-apps/ — but runs the same code.
#
# Build: make docker.build      (passes --build-arg GIT_SHA=$(git rev-parse HEAD))

FROM python:3.14-slim AS builder
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN python -m venv /opt/venv
COPY pyproject.toml README.md ./
COPY app ./app
RUN /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install .

FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/opt/venv/bin:$PATH"
# Non-root: Azure Container Apps and most platforms allow it; nothing here needs root.
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
# .dockerignore keeps this to app/, alembic/, alembic.ini and packaging metadata.
COPY --chown=appuser:appuser . .
USER appuser

# Release identity for /health and error reporting. Passed by the build workflow
# as the deploying commit; absent in a local build, where /health reports null.
# Declared after the COPY so changing it does not invalidate the layers above.
ARG GIT_SHA=""
ENV RELEASE_SHA=$GIT_SHA

EXPOSE 8000
# No --workers on purpose: uvicorn reads $WEB_CONCURRENCY, so each environment
# sets its worker count next to the CPU it has. PORT is honoured for platforms
# that inject one (Azure Container Apps, Databricks Apps via DATABRICKS_APP_PORT).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
