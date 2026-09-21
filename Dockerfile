FROM python:3.11-slim

# Install system dependencies for FFmpeg, OpenCV, and C-compilation
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port 7860 (Hugging Face Spaces default port & Render compatible)
EXPOSE 7860

# Start FastAPI backend engine
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
