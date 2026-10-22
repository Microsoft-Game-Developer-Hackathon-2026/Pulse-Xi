# Build the committed Vite application with the repository's lockfile.
FROM node:24-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53 AS frontend-build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Keep the runtime Python-only; optional Foundry SDKs are not installed.
FROM python:3.13-slim-bookworm@sha256:e32be0e55814a08977501ca863271d9bd02443710db8f2afaf8372e2c4508530 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PULSE_DEPLOYMENT_MODE=public-readonly \
    PULSE_RUNTIME_DRIVER=0 \
    PULSE_DB_PATH=/tmp/pulse-xi/imported.sqlite \
    PULSE_RUNTIME_DB_PATH=/tmp/pulse-xi/runtime.sqlite \
    PULSE_ENABLE_FOUNDRY=false
WORKDIR /app
COPY backend/requirements-runtime.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt \
    && mkdir -p /tmp/pulse-xi \
    && chown -R 10001:10001 /tmp/pulse-xi
COPY --chown=10001:10001 backend/app /app/backend/app
COPY --from=frontend-build --chown=10001:10001 /src/frontend/dist /app/frontend/dist
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8080')+'/ready',timeout=2)" || exit 1
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --app-dir /app/backend --loop app.local_event_loop:create_loop --host 0.0.0.0 --port ${PORT:-8080} --limit-concurrency 32 --no-access-log --timeout-graceful-shutdown 10"]
