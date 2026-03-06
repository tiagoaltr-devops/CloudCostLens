from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ResourceRecord(BaseModel):
    tenancy: str
    region: str
    compartment: str
    resource_type: str
    resource_id: str
    resource_name: str
    tags: dict[str, str] = Field(default_factory=dict)
    lifecycle_state: str | None = None
    creation_time: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class DailyCostSummary(BaseModel):
    date: date
    tenancy: str
    region: str
    compartment: str
    resource_type: str
    resource_id: str
    resource_name: str
    tags: dict[str, str] = Field(default_factory=dict)
    cost_components: dict[str, float] = Field(default_factory=dict)
    total_daily_cost: float
