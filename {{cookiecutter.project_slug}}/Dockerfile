# ---- Stage 1: Builder ----
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# The dev compose stack runs config.settings.dev, which imports
# debug_toolbar/django_extensions from the dev dependency group. Production
# builds stay lean by leaving INSTALL_DEV at false.
ARG INSTALL_DEV=false

# uv.lock is generated at project creation, so builds are reproducible.
# Regenerate it with `just lock` whenever pyproject.toml changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --locked --no-install-project; \
    else \
        uv sync --locked --no-install-project --no-dev; \
    fi

# ---- Stage 2: Final runtime image ----
FROM python:3.13-slim-bookworm AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    CDN_ROOT=/cdn

# Install runtime OS packages before copying source so the layer stays cached.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot \
    && mkdir -p /cdn \
    && chown -R nonroot:nonroot /cdn

WORKDIR /app

COPY --from=builder --chown=nonroot:nonroot /app /app
COPY --chown=nonroot:nonroot ./src /app

RUN chmod +x /app/scripts/*.sh

USER nonroot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=5 \
    CMD /app/scripts/healthcheck.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
