# =============================================================================
# BoostRAG frontend — Next.js 14 Dockerfile
# =============================================================================

# ── Base ─────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS base
ENV PNPM_HOME="/pnpm" \
    PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
WORKDIR /app

# ── Deps ─────────────────────────────────────────────────────────────────────
FROM base AS deps
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

# ── Dev ──────────────────────────────────────────────────────────────────────
FROM base AS dev
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
ENV NODE_ENV=development
CMD ["pnpm", "dev"]

# ── Builder (prod) ───────────────────────────────────────────────────────────
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# ── Prod runtime ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS prod
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["pnpm", "start"]
