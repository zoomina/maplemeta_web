# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/ ./frontend/
COPY backend/ ./backend/
WORKDIR /app/frontend
RUN npm install && npm run build
# output: /app/backend/static/

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /app/backend/static ./static
EXPOSE 8080
ENV PORT=8080
CMD [uvicorn, main:app, --host, 0.0.0.0, --port, 8080]
