FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for better layer caching
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[server]"

# Copy entire project
COPY . .

# Set PYTHONPATH so both relative and absolute imports work
ENV PYTHONPATH="/app:$PYTHONPATH"

EXPOSE 7860

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]