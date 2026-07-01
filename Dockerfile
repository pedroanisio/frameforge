# syntax=docker/dockerfile:1
#
# FrameGraph SDK / MCP base image — a font-rich runtime for the toolchain.
#
# The renderers resolve a document's `font_family` *by name* through the OS font
# stack (fontconfig -> freetype, via cairosvg/Pango and the fc-match metrics
# path). A named family that isn't installed silently falls back to a generic
# serif/sans, so fidelity is bounded by how many faces the host actually has.
# This image maximizes that: the entire google/fonts corpus (thousands of faces)
# plus a broad Debian font set (full Noto, CJK, Indic, Arabic, Thai, emoji).
#
# Build:
#   docker build -t frameforge .
#   docker build -t frameforge --build-arg FONTS_APT_WILDCARD=1 .   # every fonts-* pkg
#   docker build -t frameforge --build-arg INSTALL_BROWSER=0 .      # skip chromium (cairo only)
#
# Run the MCP server (stdio) — this is what an MCP client spawns:
#   docker run --rm -i frameforge
#
# See docker/README.md for wiring the container as the `framegraph` MCP command.

# ─────────────────────────────────────────────────────────────
# Stage 1 — assemble the full google/fonts corpus (discarded after copy)
# ─────────────────────────────────────────────────────────────
FROM debian:bookworm-slim AS fonts
ARG GOOGLE_FONTS_REF=main
ENV DEBIAN_FRONTEND=noninteractive GOOGLE_FONTS_REF=${GOOGLE_FONTS_REF}
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY docker/collect-google-fonts.sh /usr/local/bin/collect-google-fonts.sh
RUN chmod +x /usr/local/bin/collect-google-fonts.sh \
 && DEST=/out/google-fonts /usr/local/bin/collect-google-fonts.sh

# ─────────────────────────────────────────────────────────────
# Stage 2 — the runtime: Python + uv + system libs + fonts + venv
# ─────────────────────────────────────────────────────────────
FROM python:3.13-slim-bookworm

# uv is the project's dependency/venv source of truth (pinned for reproducibility).
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

ARG FONTS_APT_WILDCARD=0
ARG TESSERACT_ALL=0
ARG INSTALL_BROWSER=1

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    FRAMEGRAPH_CHROMIUM_NO_SANDBOX=1

# System libraries the optional lanes dlopen at runtime:
#  - cairosvg  -> libcairo2 + pango + gdk-pixbuf (SVG->PNG for the vision loop)
#  - opencv    -> libglib2.0-0 + libgomp1 (headless wheel; no libGL)
#  - pytesseract -> the tesseract-ocr binary + language data
# plus fontconfig (fc-match/fc-cache), git+make (repo tooling), and the broad
# Debian font set from docker/fonts.apt.txt.
COPY docker/fonts.apt.txt /tmp/fonts.apt.txt
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates git make \
      fontconfig \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
      shared-mime-info libffi8 libjpeg62-turbo \
      libglib2.0-0 libgomp1 \
      tesseract-ocr tesseract-ocr-eng tesseract-ocr-osd \
 && if [ "$TESSERACT_ALL" = "1" ]; then apt-get install -y --no-install-recommends tesseract-ocr-all || true; fi \
 && FONT_PKGS="$(grep -vE '^\s*(#|$)' /tmp/fonts.apt.txt)" \
 && ( apt-get install -y --no-install-recommends $FONT_PKGS \
      || for p in $FONT_PKGS; do apt-get install -y --no-install-recommends "$p" || echo "skip font pkg: $p"; done ) \
 && if [ "$FONTS_APT_WILDCARD" = "1" ]; then apt-get install -y --no-install-recommends 'fonts-*' || true; fi \
 && rm -rf /var/lib/apt/lists/* /tmp/fonts.apt.txt

# The google/fonts corpus from stage 1, then one cache rebuild over everything.
COPY --from=fonts /out/google-fonts /usr/share/fonts/truetype/google-fonts
RUN fc-cache -f \
 && echo "fonts: $(fc-list | wc -l) faces, $(fc-list : family | sort -u | wc -l) families"

WORKDIR /app

# Dependency layer first (cache-friendly): a virtual project (package=false)
# resolves its venv from just pyproject.toml + uv.lock. --all-groups pulls the
# full toolchain: mcp, vision, browser, render, pdf, pdfout, metrics, dev.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --all-groups --frozen

# The Chromium binary for the high-fidelity raster lane (cairo is the fallback).
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$INSTALL_BROWSER" = "1" ]; then \
      uv run --frozen --no-sync playwright install --with-deps chromium ; \
    else echo "skipping chromium (INSTALL_BROWSER=0)"; fi

# Project source (see .dockerignore for what's excluded).
COPY . .
RUN chmod +x docker/*.sh

# Untrusted SDK code runs in a subprocess; the container boundary is the sandbox.
ENV FRAMEGRAPH_MCP_SESSION_ROOT=/work/sessions
VOLUME ["/work"]

HEALTHCHECK --interval=1m --timeout=10s --start-period=10s --retries=3 \
  CMD uv run --frozen --no-sync python -c "import framegraph.mcp" || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["mcp"]
