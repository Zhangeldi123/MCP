from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, TypedDict


Intent = Literal["list_by_category", "stats", "add_product", "discount", "unknown"]


class Plan(TypedDict, total=False):
    intent: Intent
    category: str
    product_id: int
    discount_percent: float
    name: str
    price: float
    in_stock: bool


class AgentState(TypedDict):
    query: str
    plan: Plan
    trace: List[str]
    answer: str
