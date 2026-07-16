FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN set -eux; \
    for attempt in 1 2 3 4 5; do \
        apt-get update \
        && apt-get install -y --no-install-recommends \
            libmagic1 \
        && break; \
        rm -rf /var/lib/apt/lists/*; \
        sleep $((attempt * 5)); \
    done; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY sql ./sql
COPY docs ./docs
COPY eval ./eval
RUN mkdir -p data

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
