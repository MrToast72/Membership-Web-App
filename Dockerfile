FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/
COPY generate_icons.py /app/
COPY Icon.png /app/ 2>/dev/null || true
COPY .env* /app/ 2>/dev/null || true

RUN mkdir -p /app/data /app/backups /app/app/static/assets

RUN python generate_icons.py /app/Icon.png /app/app/static/assets 2>/dev/null || true

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
