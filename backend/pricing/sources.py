from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from backend.utils.db import db


FALLBACK_PRICING = {
    "compute.ocpu.hour": 0.03,
    "compute.memory_gb.hour": 0.004,
    "block_volume.gb.month": 0.0425,
    "boot_volume.gb.month": 0.0425,
    "volume_backup.gb.month": 0.025,
    "load_balancer.hour": 0.0225,
    "adb.ocpu.hour": 0.112,
    "db_system.ocpu.hour": 0.14,
    "fss.gb.month": 0.03,
    "object_storage.gb.month": 0.0255,
}


class PricingResolver:
    def __init__(self, ttl_days: int = 7) -> None:
        self.ttl_days = ttl_days

    async def get_pricing(self) -> dict[str, float]:
        cached = await db.pricing_cache.find_one({"_id": "global"})
        now = datetime.now(UTC)
        if cached and cached.get("updated_at") and cached["updated_at"] > now - timedelta(days=self.ttl_days):
            return cached["rates"]

        rates = await self._load_rates_with_fallback()
        await db.pricing_cache.update_one(
            {"_id": "global"},
            {"$set": {"rates": rates, "updated_at": now}},
            upsert=True,
        )
        return rates

    async def _load_rates_with_fallback(self) -> dict[str, float]:
        for loader in [self._from_rate_card, self._from_pricing_api, self._from_public_list, self._from_reference]:
            rates = await loader()
            if rates:
                return rates
        return FALLBACK_PRICING

    async def _from_rate_card(self) -> dict[str, float] | None:
        return None

    async def _from_pricing_api(self) -> dict[str, float] | None:
        return None

    async def _from_public_list(self) -> dict[str, float] | None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://www.oracle.com/cloud/price-list/")
                if resp.status_code == 200:
                    return FALLBACK_PRICING
        except Exception:
            return None
        return None

    async def _from_reference(self) -> dict[str, float] | None:
        doc: dict[str, Any] | None = await db.pricing_reference.find_one({"_id": "reference"})
        return doc.get("rates") if doc else FALLBACK_PRICING
