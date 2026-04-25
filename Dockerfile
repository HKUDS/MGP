FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./pyproject.toml
COPY reference/ ./reference/
COPY adapters/ ./adapters/
COPY schemas/ ./schemas/
COPY openapi/ ./openapi/

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["mgp-gateway", "--host", "0.0.0.0", "--port", "8080"]
