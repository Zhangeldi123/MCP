from __future__ import annotations

import os
from fastapi import FastAPI
from pydantic import BaseModel, Field

from .agent.graph import run_agent
import logging, os

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


app = FastAPI(title="MCP + LangGraph Product Agent", version="1.0.0")


class AgentQuery(BaseModel):
    query: str = Field(..., examples=["Покажи все продукты в категории Электроника"])


@app.post("/api/v1/agent/query")
async def agent_query(payload: AgentQuery):
    return await run_agent(payload.query)


@app.get("/health")
async def health():
    return {"status": "ok", "db_path": os.getenv("PRODUCTS_DB_PATH", "/app/data/products.json")}
