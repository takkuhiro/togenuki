# TogeNuki Backend API Dockerfile
# Optimized for Cloud Run deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application source code
COPY src/ ./src/

# Copy Firebase credentials (will be overridden by Secret Manager in production)
COPY secrets/ ./secrets/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the application
# Cloud Run sets PORT environment variable
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]
