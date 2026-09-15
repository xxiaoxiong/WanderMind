FROM node:24-alpine AS frontend-build

WORKDIR /web
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend ./
RUN pnpm build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WANDERMIND_STATIC_DIR=/app/static

WORKDIR /app
RUN addgroup --system wandermind && adduser --system --ingroup wandermind wandermind

COPY backend/pyproject.toml backend/README.md backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/src ./src
RUN pip install --upgrade pip && pip install .
COPY --from=frontend-build /web/dist ./static

USER wandermind
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn wandermind.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
