FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY services/api/pyproject.toml .
RUN uv pip install --system -e .

COPY services/api/ .

CMD ["celery", "-A", "app.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=4", \
     "--max-tasks-per-child=50", \
     "-Q", "default,seo,content,publish,social,analytics"]
