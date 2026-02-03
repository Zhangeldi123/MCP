# MCP + LangGraph Product Agent (Test Task)

This repo implements:
- **MCP server** (FastMCP, stdio) with product tools
- **LangGraph agent** that connects to the MCP server via stdio subprocess
- **FastAPI** endpoint to chat with the agent
- **Dockerfile + docker-compose**
- **3+ tests**

## Project structure

```
.
├─ app/
│  ├─ api.py
│  ├─ agent/
│  │  ├─ graph.py
│  │  ├─ mcp_client.py
│  │  ├─ mock_llm.py
│  │  ├─ tools_custom.py
│  │  └─ types.py
│  └─ mcp_server/
│     ├─ products_server.py
│     └─ storage.py
├─ data/products.json
├─ tests/
│  └─ test_api.py
├─ Dockerfile
├─ docker-compose.yml
└─ requirements.txt
```

## Run with Docker Compose (recommended)

```bash
docker compose up --build
```

API будет доступен на:
- `http://localhost:8000/docs`
- endpoint: `POST http://localhost:8000/api/v1/agent/query`

Example request:

```bash
curl -X POST "http://localhost:8000/api/v1/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"Покажи все продукты в категории Электроника"}'
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export PRODUCTS_DB_PATH=./data/products.json  # Windows: set PRODUCTS_DB_PATH=...
uvicorn app.api:app --reload
```

## Tests

```bash
pytest -q
```

## Notes

- MCP server runs via **stdio** (`python app/mcp_server/products_server.py`) and is spawned by the FastMCP `Client(...)` inside the agent.
- The agent uses a **mock LLM** (rule-based) that outputs a JSON plan, then executes the plan by calling MCP tools + custom tools.
