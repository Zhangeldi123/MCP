FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App code
COPY app /app/app

# Alembic (IMPORTANT)
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

# Optional
COPY scripts /app/scripts
COPY data /app/data
COPY tests /app/tests
COPY README.md /app/README.md

# ENV for SQLite (bonus)
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/app.db
ENV ALEMBIC_DATABASE_URL=sqlite:////app/data/app.db

# MCP server script locations
ENV MCP_PRODUCTS_SERVER_SCRIPT=/app/app/mcp_server/products_server.py
ENV MCP_ORDERS_SERVER_SCRIPT=/app/app/mcp_server/orders_server.py
ENV MCP_SERVER_CMD="python -m app.mcp_server.products_server"

EXPOSE 8000

# Run migrations + (optional seed) + start API
CMD ["bash", "-lc", "alembic -c /app/alembic.ini upgrade head && python scripts/seed.py && uvicorn app.api:app --host 0.0.0.0 --port 8000"]
