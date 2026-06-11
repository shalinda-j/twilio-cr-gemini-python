FROM python:3.11-slim

# Flush stdout/stderr immediately so docker compose logs show in real time.
ENV PYTHONUNBUFFERED=1

# ffmpeg/libsndfile help audio libs; build tools for any wheels that compile.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libsndfile1 build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["python", "-m", "app.server"]
