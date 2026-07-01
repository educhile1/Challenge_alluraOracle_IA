# Use stable, official Python slim image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed for compiling packages like hnswlib if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and resource folders
COPY main.py .
COPY rag_engine.py .
COPY static/ ./static/
COPY sample_docs/ ./sample_docs/

# Create data directories inside the container
RUN mkdir -p data vector_db

# Expose FastAPI server port
EXPOSE 8000

# Execute server
CMD ["python", "main.py"]
