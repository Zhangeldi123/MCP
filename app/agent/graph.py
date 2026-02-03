from __future__ import annotations

import json
import os
from typing import Any, Dict

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from .types import AgentState, Plan
from .mock_llm import MockPlannerLLM
from .mcp_client import MCPProductsClient
from .tools_custom import calc_discount, format_products, format_statistics





async def plan_node(state: AgentState) -> AgentState:
    llm = MockPlannerLLM()
    msg = HumanMessage(content=state["query"])
    res = await llm.ainvoke([msg])
    plan: Plan = json.loads(res.content)
    state["plan"] = plan
    state["trace"].append(f"plan={plan}")
    return state


async def exec_node(state: AgentState) -> AgentState:
    plan: Dict[str, Any] = state["plan"]
    intent = plan.get("intent", "unknown")

    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////app/data/app.db")
    async with MCPProductsClient(db_url) as mcp:
        if intent == "list_by_category":
            category = plan.get("category")
            products = await mcp.list_products(category=category)
            state["answer"] = format_products.invoke({"products": products})

            state["trace"].append("called:list_products")

        elif intent == "stats":
            stats = await mcp.get_statistics()
            state["answer"] = format_statistics.invoke({"stats": stats})
            state["trace"].append("called:get_statistics")

        elif intent == "add_product":
            p = await mcp.add_product(
                name=str(plan["name"]),
                price=float(plan["price"]),
                category=str(plan["category"]),
                in_stock=bool(plan.get("in_stock", True)),
            )
            state["answer"] = "Добавлено:\n" + format_products.invoke({"products": [p]})
            state["trace"].append("called:add_product")

        elif intent == "discount":
            pid = int(plan["product_id"])
            disc = float(plan["discount_percent"])
            p = await mcp.get_product(product_id=pid)
            new_price = calc_discount.invoke({"price": float(p["price"]), "percent": disc})
            state["answer"] = (
                f'Товар: #{p["id"]} — {p["name"]}\n'
                f'Цена: {p["price"]}\n'
                f'Скидка: {disc}%\n'
                f'Цена со скидкой: {new_price:.2f}'
            )
            state["trace"].append("called:get_product+calc_discount")

        else:
            state["answer"] = (
                "Не понял запрос. Примеры:\n"
                "- Покажи все продукты в категории Электроника\n"
                "- Какая средняя цена продуктов?\n"
                "- Добавь новый продукт: Мышка, цена 1500, категория Электроника\n"
                "- Посчитай скидку 15% на товар с ID 1"
            )
            state["trace"].append("intent:unknown")

    return state


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("plan", plan_node)
    g.add_node("exec", exec_node)
    g.set_entry_point("plan")
    g.add_edge("plan", "exec")
    g.add_edge("exec", END)
    return g.compile()


GRAPH = build_graph()


async def run_agent(query: str) -> Dict[str, Any]:
    init: AgentState = {"query": query, "plan": {"intent": "unknown"}, "trace": [], "answer": ""}
    out = await GRAPH.ainvoke(init)
    return {"answer": out["answer"], "trace": out["trace"], "plan": out["plan"]}
