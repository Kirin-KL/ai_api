import asyncio
from db.database import engine, Base
import db.models  # важно: импортируем модели, чтобы SQLAlchemy их увидел


async def create_database():
    print("Создаю таблицы в базе данных...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Готово! Все таблицы успешно созданы.")


asyncio.run(create_database())
