from __future__ import annotations
from typing import Any, Dict, List
from langchain_core.tools import tool

def _plain(x: Any) -> Any:
    """Convert pydantic objects (RootModel/BaseModel) into plain python types recursively."""
    if x is None:
        return None

    # pydantic v2 BaseModel/RootModel
    if hasattr(x, "model_dump"):
        return _plain(x.model_dump())
    
    # pydantic v2 RootModel/BaseModel
    if hasattr(x, "model_dump"):
        d = x.model_dump()

        # ✅ ВАЖНО: раскрываем обёртки Root/data
        if isinstance(d, dict) and len(d) == 1:
            only_key = next(iter(d.keys()))
            if only_key in ("root", "__root__", "data"):
                return _plain(d[only_key])

        return _plain(d)

    # pydantic v1 BaseModel
    if hasattr(x, "dict"):
        return _plain(x.dict())

    # RootModel variants
    if hasattr(x, "root"):
        return _plain(getattr(x, "root"))
    if hasattr(x, "__root__"):
        return _plain(getattr(x, "__root__"))

    # sometimes MCP wraps payload as .data
    if hasattr(x, "data"):
        return _plain(getattr(x, "data"))
    
        # ✅ FastMCP wrapper types.Root (not pydantic)
    if type(x).__name__ == "Root":
        # 1) if it's iterable like a dict
        try:
            if hasattr(x, "items"):
                return _plain(dict(x.items()))
        except Exception:
            pass

        # 2) common attribute names
        for attr in ("root", "data", "value", "payload", "content"):
            if hasattr(x, attr):
                return _plain(getattr(x, attr))

        # 3) last resort: if it has __dict__
        if hasattr(x, "__dict__") and x.__dict__:
            return _plain(x.__dict__)

        # 4) nothing to unwrap
        return None


    if isinstance(x, list):
        return [_plain(i) for i in x]

    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}

    return x


@tool
def format_products(products: Any) -> str:
    """Format products list into readable text."""
    print(f"DEBUG format_products: Received type: {type(products)}")
    
    # Преобразуем в простые типы
    products = _plain(products)
    print(f"DEBUG format_products: After _plain type: {type(products)}")
    print(f"DEBUG format_products: After _plain value: {products}")
    
    # поддержка формы {"products": [...]}
    if isinstance(products, dict):
        for key in ["products", "items", "results", "data", "content"]:
            if key in products and isinstance(products[key], list):
                products = products[key]
                break
    
    if not products or (isinstance(products, list) and len(products) == 0):
        return "Ничего не найдено."
    
    # Убедимся, что это список
    if not isinstance(products, list):
        if isinstance(products, dict):
            products = [products]
        else:
            return f"Ошибка: ожидался список, получен {type(products)}"
    
    lines = []
    for i, p in enumerate(products):
        print(f"DEBUG format_products: Processing item {i}: {p}")
        
        if not isinstance(p, dict):
            print(f"DEBUG format_products: Item {i} is not dict: {type(p)}")
            continue
            
        # Безопасно получаем значения
        p_id = p.get("id", "N/A")
        name = p.get("name", "Без названия")
        price = p.get("price", 0)
        category = p.get("category", "Без категории")
        in_stock = p.get("in_stock", False)
        
        stock = "в наличии" if in_stock else "нет в наличии"
        lines.append(
            f'#{p_id} — {name} — {price} — {category} — {stock}'
        )
    
    return "\n".join(lines) if lines else "Ничего не найдено."


@tool
def calc_discount(price: float, percent: float) -> Dict[str, float]:
    """Calculate discounted price for a given price and percent."""
    discount_amount = price * (percent / 100.0)
    final_price = price - discount_amount
    return {
        "price": round(float(price), 2),
        "percent": round(float(percent), 2),
        "discount_amount": round(float(discount_amount), 2),
        "final_price": round(float(final_price), 2),
    }

@tool
def format_statistics(stats: Any) -> str:
    """Format statistics dict into readable text."""
    stats = _plain(stats)
    if isinstance(stats, dict) and "stats" in stats and isinstance(stats["stats"], dict):
        stats = stats["stats"]
    if not isinstance(stats, dict):
        return f"Ошибка: ожидался dict, получен {type(stats)}"
    if "error" in stats:
        return f"Ошибка MCP: {stats['error']}"
    return (
        f"Всего продуктов: {stats.get('count', 0)}\n"
        f"Средняя цена: {stats.get('avg_price', 0)}\n"
        f"Мин. цена: {stats.get('min_price', 0)}\n"
        f"Макс. цена: {stats.get('max_price', 0)}"
    )
