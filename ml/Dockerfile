# Fashion ML recommendation service (CPU torch)
FROM python:3.11-slim

WORKDIR /app

# System deps for opencv-headless / pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (CPU torch via PyPI default wheel)
COPY ml/requirements.txt /app/ml/requirements.txt
RUN pip install --no-cache-dir -r /app/ml/requirements.txt

# Application code + catalog data
COPY ml/ /app/ml/
COPY data/ /app/data/

ENV PYTHONPATH=/app/ml
ENV DATA_DIR=/app/data
ENV ARTIFACT_DIR=/app/data/processed
ENV PYTHONUNBUFFERED=1

WORKDIR /app/ml
EXPOSE 8000

# Note: torch CPU — omit CUDA base image for smaller footprint
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]
