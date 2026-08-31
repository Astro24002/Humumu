FROM node:20-alpine AS web-builder
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
COPY migrations ./migrations
COPY --from=web-builder /web/dist ./web/dist
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV SERVER_PORT=8080
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
