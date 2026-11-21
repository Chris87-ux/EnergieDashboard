# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci
COPY app/frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    MONGO_URL="mongodb://mongo:27017" \
    DB_NAME="energieboard"
RUN groupadd --gid 10001 energieboard \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /opt/energieboard --shell /usr/sbin/nologin energieboard \
    && python -m venv /opt/venv
COPY app/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip check
WORKDIR /opt/energieboard/app/backend
COPY --chown=10001:10001 app/backend/ ./
COPY --from=frontend --chown=10001:10001 /build/dist /opt/energieboard/app/frontend/dist
COPY --chown=10001:10001 deploy/backup.py /opt/energieboard/deploy/backup.py
COPY VERSION /opt/energieboard/VERSION
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/', timeout=3)"]
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
