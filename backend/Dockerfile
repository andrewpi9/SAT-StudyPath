FROM python:3.13-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt requirements-prod.txt ./
RUN pip install -r requirements-prod.txt

COPY app ./app

EXPOSE 8000
# $PORT is provided by most hosts (Render, Railway, Fly); default for local runs.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
