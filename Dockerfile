# Stage 1: Build frontend
FROM node:20 AS frontend-builder
WORKDIR /app
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Backend
FROM python:3.11

WORKDIR /app

# Install backend deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/server.py .

# Copy frontend static
COPY --from=frontend-builder /app/out ./static

# Expose HF port
EXPOSE 7860

# 🔥 IMPORTANT (THIS WAS MISSING)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]