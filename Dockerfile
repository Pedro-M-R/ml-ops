FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --locked --no-dev

COPY deployment/ ./deployment/
COPY reports/selection.json ./reports/selection.json

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["churn-serve", "--host", "0.0.0.0", "--port", "8000"]
