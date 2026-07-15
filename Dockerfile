# syntax=docker/dockerfile:1
# ============================================================================
# Indian Law AI Portal — single-service image (FastAPI serves the built React
# app + the API). The public statutes and the prebuilt FAISS index are baked in,
# and the embedding + reranker models are pre-downloaded, so the container needs
# no network at startup and answers immediately.
#
#   docker build -t indian-law-ai .
#   docker run -p 8000:8000 -e GROQ_API_KEY=gsk_xxx indian-law-ai
#   open http://localhost:8000
# ============================================================================

# ---- Stage 1: build the React frontend ----
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install
COPY frontend/ ./
ENV CI=false
RUN npm run build

# ---- Stage 2: python runtime ----
FROM python:3.11-slim AS runtime

# Runtime libs for faiss / torch, and curl for the healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch first — keeps the image ~1GB instead of pulling the CUDA build
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Application dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the local models so cold starts need no network
ENV HF_HOME=/root/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-small-en-v1.5'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L6-v2')"

# App code + baked corpus + prebuilt index + built frontend
COPY backend/ ./backend/
COPY assets/ ./assets/
COPY vector_db/ ./vector_db/
COPY --from=frontend /frontend/build ./frontend/build

# Production defaults. Override at deploy time; GROQ_API_KEY MUST be supplied.
ENV DEBUG_MODE=false \
    LLM_PROVIDER=groq \
    GROQ_MODEL=openai/gpt-oss-20b \
    EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
    RATE_LIMIT_ENABLED=true \
    DAILY_QUERY_LIMIT=25 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Hosting platforms inject $PORT; backend/main.py honours it (defaults to 8000).
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsSL "http://localhost:${PORT:-8000}/health/" || exit 1

# Launched from the project root exactly like local (relative paths resolve
# against it). DEBUG_MODE=false => no reload => single process (correct for the
# in-memory daily-quota counter).
CMD ["python", "backend/main.py"]
