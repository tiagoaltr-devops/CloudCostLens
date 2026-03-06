from motor.motor_asyncio import AsyncIOMotorClient

from backend.utils.config import settings


client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.mongo_db]


async def ensure_indexes() -> None:
    await db.daily_cost_summary.create_index([
        ("date", 1),
        ("region", 1),
        ("compartment", 1),
        ("resource_type", 1),
    ])
    await db.daily_cost_summary.create_index("resource_id")
    await db.daily_cost_summary.create_index("tags")
    await db.pricing_cache.create_index("updated_at")
