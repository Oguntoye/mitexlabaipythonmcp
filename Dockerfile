FROM python:3.13-slim AS builder
ARG TARGET_BRANCH
ENV UV_HTTP_TIMEOUT=300
ENV UV_HTTP_RETRIES=5
RUN apt-get update && apt-get install -y git gcc libc6-dev libffi-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy source code first (but exclude uv.lock if it exists locally)
COPY pyproject.toml ./
COPY src ./src
COPY main.py ./

# Make git use your PAT for ALL GitHub HTTPS fetches during this stage
RUN --mount=type=secret,id=private_token \
    PRIVATE_TOKEN=$(cat /run/secrets/private_token) && \
    git config --global url."https://oguntoye:${PRIVATE_TOKEN}@github.com/".insteadOf "https://github.com"

# Install base dependencies
RUN uv sync

# Add private dependency using build secret with specified branch
RUN --mount=type=secret,id=private_token \
   PRIVATE_TOKEN=$(cat /run/secrets/private_token) && \
   uv add git+https://oguntoye:$PRIVATE_TOKEN@github.com/oguntoye/mitexlab_googlemcp.git#$TARGET_BRANCH && \
   uv lock --upgrade-package mitexlab-googlemcp && \
   uv sync

# Add private dependency using build secret with specified branch
RUN --mount=type=secret,id=private_token \
   PRIVATE_TOKEN=$(cat /run/secrets/private_token) && \
   uv add git+https://oguntoye:$PRIVATE_TOKEN@github.com/oguntoye/mitexlab_instagrammcp.git#$TARGET_BRANCH && \
   uv lock --upgrade-package mitexlab-instagrammcp && \
   uv sync

RUN --mount=type=secret,id=private_token \
   PRIVATE_TOKEN=$(cat /run/secrets/private_token) && \
   uv add git+https://oguntoye:$PRIVATE_TOKEN@github.com/oguntoye/mitex_mailer_mcp.git#$TARGET_BRANCH && \
   uv lock --upgrade-package mitex-mailer-mcp && \
   uv sync

# Run type checking
RUN uv run mypy src

# Production stage
FROM python:3.13-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy built dependencies and project files (including uv.lock)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/uv.lock ./
COPY --from=builder /app/src ./src
COPY --from=builder /app/main.py ./

CMD ["uv", "run", "main.py"]