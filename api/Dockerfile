# SimpleResume API — production Dockerfile (placeholder)
#
# Build:  docker build -t simpleresume-api .
# Run:    docker run -p 8000:8000 --env-file .env simpleresume-api
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
