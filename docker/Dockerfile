FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for caching
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/
COPY config.yaml* ./

# Non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.webhook.server:app", "--host", "0.0.0.0", "--port", "8000"]
