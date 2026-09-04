# Mandol-AML service image.
#
# Build context MUST be the root of a fork of AgentCombo/Mandol that already
# contains the additive files from this overlay (src/mandol_aml, Dockerfile,
# docker-compose.yml, aml.env.example). Mandol's own pyproject.toml / uv.lock
# are used unchanged; this image only ADDS the AML HTTP adapter on top.
#
# CPU build (default):
#   docker build -t mandol-aml:0.1.0-aml.1 .
# GPU build (optional; needs the nvidia container toolkit):
#   docker build --build-arg BASE_IMAGE=nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04 -t mandol-aml:0.1.0-aml.1 .
#
# The image is large because Mandol's runtime pins torch 2.8.0. First startup
# may download the embedding model (default BAAI/bge-m3) - /health returns 503
# until warm-up finishes.

ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/src

# uv (Python package manager used by Mandol's pyproject; pin a specific tag for reproducible builds)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Runtime system libraries for torch / faiss / rocksdict / tokenizers
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libgl1 \
        libglib2.0-0 \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Mandol + mandol_aml runtime dependencies (no dev/docs extras).
# Mandol requires Python >=3.12,<3.13 (image base already satisfies this).
COPY pyproject.toml uv.lock README_PYPI.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Default AML service settings (override via environment / aml.env.example).
ENV AML_HOST=0.0.0.0 \
    AML_PORT=8000 \
    AML_ADD_PATH=/add \
    AML_SEARCH_PATH=/search \
    AML_HEALTH_PATH=/health \
    AML_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B

EXPOSE 8000

# Healthcheck used by the platform / orchestrator.
HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health > /dev/null || exit 1

CMD ["uv", "run", "python", "-m", "mandol_aml"]
