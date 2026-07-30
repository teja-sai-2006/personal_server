# Dockerfile for FastAPI backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for Pillow compilation or network utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose backend port
EXPOSE 8000

# Start FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
