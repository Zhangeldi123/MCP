import os
import pytest
from pathlib import Path

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.api import app
from app.db import Base
from app.models import Product


@pytest.fixture(autouse=True)
async def _set_test_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Create a temporary SQLite DB for tests
    db_file = tmp_path / "app.db"
    db_url = f"sqlite+aiosqlite:////{db_file}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", db_url.replace("+aiosqlite", ""))

    # Create schema + seed data
    engine = create_async_engine(db_url, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        s.add_all([
            Product(name="Ноутбук", price=50000, category="Электроника", in_stock=True),
            Product(name="Кофе", price=1200, category="Продукты", in_stock=False),
        ])
        await s.commit()

    yield

    await engine.dispose()


@pytest.mark.asyncio
async def test_list_by_category():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/agent/query", json={"query": "Покажи все продукты в категории Электроника"})
        assert r.status_code == 200
        data = r.json()
        assert "#1" in data["answer"]
        assert "Ноутбук" in data["answer"]
        assert "Кофе" not in data["answer"]


@pytest.mark.asyncio
async def test_statistics_average_price():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/agent/query", json={"query": "Какая средняя цена продуктов?"})
        assert r.status_code == 200
        data = r.json()
        # avg of 50000 and 1200 = 25600
        assert "Средняя цена" in data["answer"]
        assert "25600" in data["answer"]


@pytest.mark.asyncio
async def test_discount():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/agent/query", json={"query": "Посчитай скидку 15% на товар с ID 1"})
        assert r.status_code == 200
        data = r.json()
        assert "Цена со скидкой" in data["answer"]
        # 50000 * 0.85 = 42500
        assert "42500" in data["answer"]
