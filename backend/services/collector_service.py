from __future__ import annotations

from datetime import UTC, datetime

from backend.collectors.oci_collector import OCICollector
from backend.pricing.sources import PricingResolver
from backend.services.cost_engine import CostEngine
from backend.utils.db import db


class CollectorService:
    def __init__(self) -> None:
        self.collector = OCICollector()
        self.pricing = PricingResolver()

    async def run_daily_collection(self) -> int:
        resources = await self.collector.collect_inventory()
        rates = await self.pricing.get_pricing()
        engine = CostEngine(rates)
        today = datetime.now(UTC).date()
        summaries = engine.calculate(resources, today)

        await db.daily_cost_summary.delete_many({"date": today.isoformat()})
        if summaries:
            await db.daily_cost_summary.insert_many([s.model_dump(mode="json") for s in summaries])
        return len(summaries)
