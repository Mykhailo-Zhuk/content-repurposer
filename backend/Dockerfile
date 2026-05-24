FROM python:3.11-slim

# Install system dependencies (ffmpeg required for video processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create job storage directory
RUN mkdir -p /tmp/repurposer_jobs

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
