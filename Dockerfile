# AI Change Impact Analyzer
# Single image for the API and the Streamlit UI.
# Runs on Hugging Face Spaces (UI on port 7860) and with docker-compose locally.

FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user with UID 1000 (required by Hugging Face Spaces)
RUN useradd -m -u 1000 appuser

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY streamlit_app/ ./streamlit_app/
COPY evaluation/ ./evaluation/
COPY prompts/ ./prompts/
COPY data/documents/ ./data/documents/
COPY start.sh ./start.sh

# Create data directories
RUN mkdir -p data/chroma_db data/uploads logs evaluation/reports .cache \
    && chmod +x start.sh \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/appuser
ENV FASTEMBED_CACHE_PATH=/app/.cache/fastembed

# Download the in-process embedding model at build time so cold starts are fast
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/app/.cache/fastembed')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# API on 8000 (internal), Streamlit UI on 7860
EXPOSE 8000 7860
CMD ["./start.sh"]
