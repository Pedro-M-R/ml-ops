FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY src/ ./src/
RUN uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"
CMD ["churn-train"]
