from __future__ import annotations

import json
import re
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class MockPlannerLLM(BaseChatModel):
    """A deterministic mock chat model that outputs a JSON plan.

    It supports Russian queries like:
    - "Покажи все продукты в категории Электроника"
    - "Какая средняя цена продуктов?"
    - "Добавь новый продукт: Мышка, цена 1500, категория Электроника"
    - "Посчитай скидку 15% на товар с ID 1"
    """

    model_name: str = "mock-planner-llm"

    def _extract_text(self, messages: List[BaseMessage]) -> str:
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                return m.content
        return messages[-1].content if messages else ""

    def _plan(self, text: str) -> dict:
        t = text.strip()

        # list by category
        m = re.search(r"категори[ия]\s+([\w\-]+)", t, flags=re.IGNORECASE)
        if ("покажи" in t.lower() or "показать" in t.lower() or "выведи" in t.lower()) and m:
            return {"intent": "list_by_category", "category": m.group(1)}

        # statistics / average price
        if re.search(r"средн(яя|юю)\s+цен", t, flags=re.IGNORECASE) or "статист" in t.lower():
            return {"intent": "stats"}

        # add product
        if t.lower().startswith("добавь") or t.lower().startswith("добавить"):
            # "Добавь новый продукт: Мышка, цена 1500, категория Электроника"
            name = None
            price = None
            category = None
            in_stock = True

            m_name = re.search(r"продукт\s*:\s*([^,]+)", t, flags=re.IGNORECASE)
            if m_name:
                name = m_name.group(1).strip()

            m_price = re.search(r"цен[аы]\s*(\d+(?:[\.,]\d+)?)", t, flags=re.IGNORECASE)
            if m_price:
                price = float(m_price.group(1).replace(",", "."))

            m_cat = re.search(r"категори[ия]\s*([\w\-]+)", t, flags=re.IGNORECASE)
            if m_cat:
                category = m_cat.group(1).strip()

            if name and price is not None and category:
                return {"intent": "add_product", "name": name, "price": price, "category": category, "in_stock": in_stock}

        # discount
        m_disc = re.search(r"скидк\w*\s*(\d+(?:[\.,]\d+)?)%?", t, flags=re.IGNORECASE)
        m_id = re.search(r"(?:id|ID)\s*(\d+)", t)
        if m_disc and m_id:
            disc = float(m_disc.group(1).replace(",", "."))
            pid = int(m_id.group(1))
            return {"intent": "discount", "discount_percent": disc, "product_id": pid}

        return {"intent": "unknown"}

    @property
    def _llm_type(self) -> str:
        return "mock_planner"

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        text = self._extract_text(messages)
        plan = self._plan(text)
        content = json.dumps(plan, ensure_ascii=False)
        gen = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(generations=[gen])

    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        return self._generate(messages, stop=stop, **kwargs)
