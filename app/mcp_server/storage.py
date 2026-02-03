from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio


@dataclass
class Product:
    id: int
    name: str
    price: float
    category: str
    in_stock: bool

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Product":
        return Product(
            id=int(d["id"]),
            name=str(d["name"]),
            price=float(d["price"]),
            category=str(d["category"]),
            in_stock=bool(d["in_stock"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "category": self.category,
            "in_stock": self.in_stock,
        }


class ProductStore:
    """Simple JSON-backed storage with an async lock.

    The MCP server is a subprocess (stdio transport), so persistence is done by writing to a JSON file.
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._lock = asyncio.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_raw([])

    def _read_raw(self) -> List[Dict[str, Any]]:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_raw(self, data: List[Dict[str, Any]]) -> None:
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    async def list_products(self, category: Optional[str] = None) -> List[Product]:
        async with self._lock:
            items = [Product.from_dict(x) for x in self._read_raw()]
        if category:
            return [p for p in items if p.category.lower() == category.lower()]
        return items

    async def get_product(self, product_id: int) -> Product:
        async with self._lock:
            items = [Product.from_dict(x) for x in self._read_raw()]
        for p in items:
            if p.id == product_id:
                return p
        raise ValueError(f"Product with id={product_id} not found")

    async def add_product(self, name: str, price: float, category: str, in_stock: bool = True) -> Product:
        async with self._lock:
            raw = self._read_raw()
            products = [Product.from_dict(x) for x in raw]
            next_id = (max((p.id for p in products), default=0) + 1)
            new_p = Product(id=next_id, name=name, price=float(price), category=category, in_stock=bool(in_stock))
            raw.append(new_p.to_dict())
            self._write_raw(raw)
        return new_p

    async def get_statistics(self) -> Dict[str, Any]:
        products = await self.list_products()
        count = len(products)
        avg_price = (sum(p.price for p in products) / count) if count else 0.0
        return {"count": count, "avg_price": avg_price}
