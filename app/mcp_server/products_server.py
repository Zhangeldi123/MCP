from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Product


mcp = FastMCP(
    "Products MCP Server",
    instructions="Tools: list_products, get_product, add_product, get_statistics",
)


def _p_to_dict(p: Product) -> Dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "price": float(p.price),
        "category": p.category,
        "in_stock": bool(p.in_stock),
    }


def _norm_text(s: str) -> str:
    return " ".join(str(s).replace("\u00A0", " ").split()).strip()


@mcp.tool
async def list_products(category: Optional[str] = None) -> List[Dict[str, Any]]:
    async with SessionLocal() as s:
        stmt = select(Product).order_by(Product.id.asc())
        if category:
            cat = " ".join(str(category).replace("\u00A0", " ").split()).strip()
            stmt = stmt.where(func.lower(Product.category) == func.lower(cat))
        rows = (await s.execute(stmt)).scalars().all()
        return [_p_to_dict(p) for p in rows]


@mcp.tool
async def get_product(id: int) -> Dict[str, Any]:
    """Получить продукт по id. Если не найден — error."""
    try:
        async with SessionLocal() as s:
            p = await s.get(Product, int(id))
            if not p:
                return {"error": f"Product with id={id} not found"}
            return _p_to_dict(p)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
async def add_product(name: str, price: float, category: str, in_stock: bool = True) -> Dict[str, Any]:
    """Добавить продукт и вернуть созданную запись."""
    try:
        if not name or not category:
            return {"error": "name and category are required"}
        if float(price) < 0:
            return {"error": "price must be >= 0"}

        async with SessionLocal() as s:
            p = Product(
                name=str(name),
                price=float(price),
                category=str(category),
                in_stock=bool(in_stock),
            )
            s.add(p)
            await s.commit()
            await s.refresh(p)
            return _p_to_dict(p)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
async def get_statistics() -> Dict[str, Any]:
    """Статистика: count, avg_price, min_price, max_price."""
    try:
        async with SessionLocal() as s:
            stmt = select(
                func.count(Product.id),
                func.avg(Product.price),
                func.min(Product.price),
                func.max(Product.price),
            )
            count, avg_, min_, max_ = (await s.execute(stmt)).one()
            return {
                "count": int(count or 0),
                "avg_price": float(avg_ or 0.0),
                "min_price": float(min_ or 0.0),
                "max_price": float(max_ or 0.0),
            }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
