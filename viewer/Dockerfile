# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────
# Stage 1 — build the IIFE bundle with esbuild
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app

# Install deps against the committed lockfile for reproducible builds.
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the source and build dev/bundle.js.
COPY . .
RUN npm run build

# ─────────────────────────────────────────────────────────────
# Stage 2 — serve everything statically with directory browsing
# ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Our site config turns on autoindex so every file is navigable.
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Landing page linking to the app + all browsable content.
COPY docker/index.html /usr/share/nginx/html/index.html

# All viewer content (built bundle included), node_modules left behind.
COPY --from=build /app/dev            /usr/share/nginx/html/dev
COPY --from=build /app/demo           /usr/share/nginx/html/demo
COPY --from=build /app/verification   /usr/share/nginx/html/verification
COPY --from=build /app/framegraph-viewer.jsx /usr/share/nginx/html/framegraph-viewer.jsx
COPY --from=build /app/README.md      /usr/share/nginx/html/README.md

EXPOSE 80

# Lightweight liveness check.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
