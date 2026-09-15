FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN addgroup --system wandermind && adduser --system --ingroup wandermind wandermind

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN pip install --upgrade pip && pip install .

USER wandermind
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn wandermind.main:app --host 0.0.0.0 --port 8000"]
