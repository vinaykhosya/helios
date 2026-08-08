import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:admin-genesis@db.tyajlotsxwocxxawcwta.supabase.co:5432/postgres")

async def test_supabase():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema IN ('helios', 'public');"))
        rows = res.fetchall()
        print("\n=== SUPABASE TABLES FOUND ===")
        for schema, table in rows:
            print(f" - {schema}.{table}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_supabase())
