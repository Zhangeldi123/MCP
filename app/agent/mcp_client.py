from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def _to_plain(x: Any) -> Any:
    """Convert nested structures / pydantic models into plain python types."""
    if x is None:
        return None

    # pydantic v2 BaseModel / RootModel
    if hasattr(x, "model_dump"):
        return _to_plain(x.model_dump())

    # pydantic v1 BaseModel
    if hasattr(x, "dict"):
        return _to_plain(x.dict())

    # RootModel variants
    if hasattr(x, "root"):
        return _to_plain(getattr(x, "root"))
    if hasattr(x, "__root__"):
        return _to_plain(getattr(x, "__root__"))

    # sometimes wrappers use .data
    if hasattr(x, "data"):
        return _to_plain(getattr(x, "data"))

    if isinstance(x, list):
        return [_to_plain(i) for i in x]

    if isinstance(x, dict):
        return {k: _to_plain(v) for k, v in x.items()}

    return x


def _extract_payload(res: Any) -> Any:
    """
    FastMCP 2.14.x: real tool output is often in res.content as TextContent with JSON string.
    res.data in your setup is [Root(), ...] placeholders (types.Root), so we ignore it.
    """
    # 1) MCP content blocks
    content = getattr(res, "content", None)
    if content:
        # content is usually a list; in your logs it's [TextContent(type='text', text='[...]')]
        # Try parse first text block
        c0 = content[0]

        # dict-like block
        if isinstance(c0, dict):
            # some versions may send {"type":"text","text":"...json..."}
            text = c0.get("text")
            if isinstance(text, str) and text.strip():
                try:
                    return json.loads(text)
                except Exception:
                    return text

            # or {"type":"json","json":{...}}
            if "json" in c0:
                return c0["json"]

        # object-like block (TextContent / JsonContent)
        text = getattr(c0, "text", None)
        if isinstance(text, str) and text.strip():
            try:
                return json.loads(text)
            except Exception:
                return text

        js = getattr(c0, "json", None)
        if js is not None:
            return js

    # 2) pydantic-like dump of result (sometimes contains content/data)
    if hasattr(res, "model_dump"):
        d = res.model_dump()
        if isinstance(d, dict):
            # prefer content (most reliable in your case)
            if d.get("content"):
                try:
                    c0 = d["content"][0]
                    if isinstance(c0, dict) and isinstance(c0.get("text"), str):
                        return json.loads(c0["text"])
                except Exception:
                    pass
                return d["content"]

            # fallback
            for key in ("result", "value", "data", "message"):
                v = d.get(key)
                if v not in (None, [], {}, "Root()"):
                    return v

    # 3) last resort: direct attributes
    for key in ("result", "value", "message"):
        if hasattr(res, key):
            v = getattr(res, key)
            if v not in (None, [], {}, "Root()"):
                return v

    return None


class MCPProductsClient:
    def __init__(self, db_url: str) -> None:
        # Keep base environment (PATH etc.), override only what we need
        base_env = os.environ.copy()
        base_env["DATABASE_URL"] = db_url
        base_env["PYTHONPATH"] = "/app"

        transport = StdioTransport(
            command=sys.executable,
            args=["-m", "app.mcp_server.products_server"],
            env=base_env,
            cwd="/app",
        )
        self._client = Client(transport)

    async def __aenter__(self) -> "MCPProductsClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.__aexit__(exc_type, exc, tb)

    async def list_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        res = await self._client.call_tool("list_products", {"category": category})
        payload = _extract_payload(res)
        out = _to_plain(payload)

        # Normalize: sometimes payload could be a JSON string if parsing failed
        if isinstance(out, str):
            try:
                out = json.loads(out)
            except Exception:
                pass

        # Ensure list return
        return out if isinstance(out, list) else ([] if out is None else [out])  # type: ignore[return-value]

    async def get_product(self, product_id: int) -> Dict[str, Any]:
        res = await self._client.call_tool("get_product", {"id": int(product_id)})
        payload = _extract_payload(res)
        out = _to_plain(payload)

        if isinstance(out, str):
            try:
                out = json.loads(out)
            except Exception:
                pass

        return out if isinstance(out, dict) else {"error": "Invalid tool payload", "raw": str(out)}

    async def add_product(self, name: str, price: float, category: str, in_stock: bool = True) -> Dict[str, Any]:
        res = await self._client.call_tool(
            "add_product",
            {"name": name, "price": float(price), "category": category, "in_stock": bool(in_stock)},
        )
        payload = _extract_payload(res)
        out = _to_plain(payload)

        if isinstance(out, str):
            try:
                out = json.loads(out)
            except Exception:
                pass

        return out if isinstance(out, dict) else {"error": "Invalid tool payload", "raw": str(out)}

    async def get_statistics(self) -> Dict[str, Any]:
        res = await self._client.call_tool("get_statistics", {})
        payload = _extract_payload(res)
        out = _to_plain(payload)

        if isinstance(out, str):
            try:
                out = json.loads(out)
            except Exception:
                pass

        return out if isinstance(out, dict) else {"error": "Invalid tool payload", "raw": str(out)}
