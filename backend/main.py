from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from backend.api.routes import router
from backend.services.collector_service import CollectorService
from backend.utils.config import settings
from backend.utils.db import ensure_indexes

collector = CollectorService()
scheduler = AsyncIOScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_indexes()
    if settings.scheduler_enabled:
        scheduler.add_job(collector.run_daily_collection, "cron", hour=settings.collection_hour_utc, minute=0, id="daily-collector", replace_existing=True)
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="CloudCostLens API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/collector/run")
async def trigger_collection() -> dict[str, int]:
    count = await collector.run_daily_collection()
    return {"processed_resources": count}
