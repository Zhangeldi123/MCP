from __future__ import annotations

from typing import Any, Dict, List

from fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Product, Order


mcp = FastMCP("Orders MCP Server", instructions="Tools: create_order, list_orders, get_order")


@mcp.tool
async def create_order(product_id: int, quantity: int) -> Dict[str, Any]:
    """Создать заказ. ValueError если товара нет или quantity <= 0."""
    if quantity <= 0:
        raise ValueError("quantity must be > 0")

    async with SessionLocal() as s:
        p = await s.get(Product, product_id)
        if not p:
            raise ValueError(f"Product with id={product_id} not found")

        total = float(p.price) * int(quantity)
        order = Order(product_id=product_id, quantity=quantity, total_price=total)
        s.add(order)
        await s.commit()
        await s.refresh(order)

        return {
            "id": order.id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "total_price": order.total_price,
            "created_at": order.created_at.isoformat(),
        }


@mcp.tool
async def get_order(id: int) -> Dict[str, Any]:
    """Получить заказ по id. ValueError если не найден."""
    async with SessionLocal() as s:
        o = await s.get(Order, id)
        if not o:
            raise ValueError(f"Order with id={id} not found")
        return {
            "id": o.id,
            "product_id": o.product_id,
            "quantity": o.quantity,
            "total_price": o.total_price,
            "created_at": o.created_at.isoformat(),
        }


@mcp.tool
async def list_orders() -> List[Dict[str, Any]]:
    """Список всех заказов."""
    async with SessionLocal() as s:
        rows = (await s.execute(select(Order).order_by(Order.id.desc()))).scalars().all()
        return [
            {
                "id": o.id,
                "product_id": o.product_id,
                "quantity": o.quantity,
                "total_price": o.total_price,
                "created_at": o.created_at.isoformat(),
            }
            for o in rows
        ]


if __name__ == "__main__":
    mcp.run()  # stdio
