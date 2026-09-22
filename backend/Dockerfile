FROM node:20-alpine AS base

WORKDIR /app

ENV NODE_ENV=production
ENV DATA_DIR=/app/data

COPY backend/package.json ./
RUN npm install --omit=dev && npm cache clean --force

COPY backend/src ./src
COPY data ./data

USER node

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:4000/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "src/index.js"]
