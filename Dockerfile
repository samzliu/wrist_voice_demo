# Stage 1: Build Next.js
FROM node:20-alpine AS frontend
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ ./
ARG NEXT_PUBLIC_LIVEKIT_URL
ENV NEXT_PUBLIC_LIVEKIT_URL=$NEXT_PUBLIC_LIVEKIT_URL
RUN npm run build

# Stage 2: Python + Node runtime
FROM python:3.12-slim
WORKDIR /app

# Install Node.js (needed for Next.js server with API routes)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copy source
COPY src/ src/
COPY start.sh ./
RUN chmod +x start.sh

# Copy built Next.js app (standalone + static)
COPY --from=frontend /app/web/.next web/.next
COPY --from=frontend /app/web/node_modules web/node_modules
COPY --from=frontend /app/web/package.json web/package.json
COPY --from=frontend /app/web/next.config.ts web/next.config.ts

ENV PORT=8080
EXPOSE 8080

CMD ["./start.sh"]
