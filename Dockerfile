# syntax=docker/dockerfile:1

# Builder and runtime deliberately share the same base image (python:3.12-slim-bookworm).
# uv's own venv is symlink-based, not relocatable across different Python builds, so
# building on ghcr.io/astral-sh/uv's image and copying .venv into a plain python:3.12
# runtime silently resolves to the runtime's *system* interpreter (no venv, no
# dependencies) instead of failing loudly — pulling in only the uv binary avoids that.
FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.17 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm AS runtime
RUN addgroup --system uniware && adduser --system --ingroup uniware --home /app uniware
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /app/.venv /app/.venv
COPY --chown=uniware:uniware . .
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /app/staticfiles && chown -R uniware:uniware /app/staticfiles

USER uniware
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
