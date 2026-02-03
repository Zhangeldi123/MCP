import asyncio
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Product
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main():
    async with SessionLocal() as s:
        exists = (await s.execute(select(Product.id).limit(1))).first()
        if exists:
            print("Seed: products already exist, skip")
            return

        s.add_all([
            Product(name="Ноутбук", price=50000, category="Электроника", in_stock=True),
            Product(name="Мышка", price=1500, category="Электроника", in_stock=True),
            Product(name="Кофе", price=1200, category="Продукты", in_stock=False),
        ])
        await s.commit()
        print("Seed inserted")

if __name__ == "__main__":
    asyncio.run(main())
