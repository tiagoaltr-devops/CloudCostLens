from __future__ import annotations

from datetime import date

from backend.models.cost import DailyCostSummary, ResourceRecord


class CostEngine:
    def __init__(self, rates: dict[str, float]) -> None:
        self.rates = rates

    def calculate(self, resources: list[ResourceRecord], for_date: date) -> list[DailyCostSummary]:
        return [self._calculate_resource_cost(resource, for_date) for resource in resources]

    def _calculate_resource_cost(self, r: ResourceRecord, for_date: date) -> DailyCostSummary:
        c: dict[str, float] = {}
        a = r.attributes
        if r.resource_type == "compute_instance":
            c["ocpu"] = float(a.get("ocpus", 1)) * self.rates["compute.ocpu.hour"] * 24
            c["memory"] = float(a.get("memory_gb", 1)) * self.rates["compute.memory_gb.hour"] * 24
            c["boot_volume"] = float(a.get("boot_volume_gb", 50)) * self.rates["boot_volume.gb.month"] / 30
            c["block_volume"] = float(a.get("block_volume_gb", 0)) * self.rates["block_volume.gb.month"] / 30
            c["backup"] = float(a.get("backup_gb", 0)) * self.rates["volume_backup.gb.month"] / 30
        elif r.resource_type in {"db_system", "autonomous_database"}:
            key = "db_system.ocpu.hour" if r.resource_type == "db_system" else "adb.ocpu.hour"
            c["ocpu"] = float(a.get("ocpus", 1)) * self.rates[key] * 24
        elif r.resource_type == "load_balancer":
            c["lb"] = self.rates["load_balancer.hour"] * 24
        elif r.resource_type == "file_storage":
            c["storage"] = float(a.get("size_gb", 1)) * self.rates["fss.gb.month"] / 30
        elif r.resource_type == "object_bucket":
            c["storage"] = float(a.get("size_gb", 1)) * self.rates["object_storage.gb.month"] / 30
        elif r.resource_type == "block_volume":
            c["storage"] = float(a.get("size_gb", 1)) * self.rates["block_volume.gb.month"] / 30
        elif r.resource_type == "boot_volume":
            c["storage"] = float(a.get("size_gb", 1)) * self.rates["boot_volume.gb.month"] / 30
        elif r.resource_type == "volume_backup":
            c["storage"] = float(a.get("size_gb", 1)) * self.rates["volume_backup.gb.month"] / 30
        else:
            c["estimated"] = 0.0

        total = round(sum(c.values()), 4)
        rounded = {k: round(v, 4) for k, v in c.items()}
        return DailyCostSummary(
            date=for_date,
            tenancy=r.tenancy,
            region=r.region,
            compartment=r.compartment,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            resource_name=r.resource_name,
            tags=r.tags,
            cost_components=rounded,
            total_daily_cost=total,
        )
