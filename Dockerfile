FROM python:3.10-slim

# Install system dependencies including Tesseract OCR for scanned docs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency requirements
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download tiktoken encoding for cl100k_base offline availability
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

# Pre-cache sentence-transformers/all-MiniLM-L6-v2 model for instant offline embedding
RUN python -c "from chromadb.utils import embedding_functions; fn = embedding_functions.DefaultEmbeddingFunction(); fn(['warmup'])"

# Copy application source code and tests
COPY src/ ./src/
COPY tests/ ./tests/
COPY Makefile .
COPY README.md .
COPY DESIGN.md .
COPY .env.example .

# Default environment variables pointing to ./data
ENV CORPUS_DIR=/app/data/corpus \
    MANIFEST_PATH=/app/data/manifest.json \
    DB_PATH=/app/data/veltrix.db \
    APP_TODAY=2026-09-15 \
    LLM_PROVIDER=gemini \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
