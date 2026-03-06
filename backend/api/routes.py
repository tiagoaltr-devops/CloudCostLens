from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse, Response

from backend.utils.db import db

router = APIRouter()


def _build_filter(
    start_date: date | None,
    end_date: date | None,
    region: str | None,
    compartment: str | None,
    service_type: str | None,
    tag: str | None,
) -> dict[str, Any]:
    q: dict[str, Any] = {}
    if start_date or end_date:
        q["date"] = {}
        if start_date:
            q["date"]["$gte"] = start_date.isoformat()
        if end_date:
            q["date"]["$lte"] = end_date.isoformat()
    if region:
        q["region"] = region
    if compartment:
        q["compartment"] = compartment
    if service_type:
        q["resource_type"] = service_type
    if tag:
        k, _, v = tag.partition(":")
        q[f"tags.{k}"] = v
    return q


@router.get("/costs/daily")
async def costs_daily(start_date: date | None = None, end_date: date | None = None, region: str | None = None, compartment: str | None = None, service_type: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
    q = _build_filter(start_date, end_date, region, compartment, service_type, tag)
    pipeline = [{"$match": q}, {"$group": {"_id": "$date", "total": {"$sum": "$total_daily_cost"}}}, {"$sort": {"_id": 1}}]
    return [{"date": x["_id"], "total_daily_cost": round(x["total"], 4)} async for x in db.daily_cost_summary.aggregate(pipeline)]


@router.get("/costs/by-resource")
async def by_resource(start_date: date | None = None, end_date: date | None = None, region: str | None = None, compartment: str | None = None, service_type: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
    q = _build_filter(start_date, end_date, region, compartment, service_type, tag)
    cursor = db.daily_cost_summary.find(q, {"_id": 0}).sort("total_daily_cost", -1)
    return [x async for x in cursor]


@router.get("/costs/by-service")
async def by_service(start_date: date | None = None, end_date: date | None = None, region: str | None = None, compartment: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
    q = _build_filter(start_date, end_date, region, compartment, None, tag)
    pipeline = [{"$match": q}, {"$group": {"_id": "$resource_type", "total": {"$sum": "$total_daily_cost"}}}, {"$sort": {"total": -1}}]
    return [{"service": x["_id"], "total_daily_cost": round(x["total"], 4)} async for x in db.daily_cost_summary.aggregate(pipeline)]


@router.get("/costs/by-compartment")
async def by_compartment(start_date: date | None = None, end_date: date | None = None, region: str | None = None, service_type: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
    q = _build_filter(start_date, end_date, region, None, service_type, tag)
    pipeline = [{"$match": q}, {"$group": {"_id": "$compartment", "total": {"$sum": "$total_daily_cost"}}}, {"$sort": {"total": -1}}]
    return [{"compartment": x["_id"], "total_daily_cost": round(x["total"], 4)} async for x in db.daily_cost_summary.aggregate(pipeline)]


@router.get("/costs/trend")
async def trend(days: int = Query(default=30, le=365)) -> list[dict[str, Any]]:
    start = (datetime.utcnow().date()).toordinal() - days
    start_date = date.fromordinal(start)
    pipeline = [{"$match": {"date": {"$gte": start_date.isoformat()}}}, {"$group": {"_id": "$date", "total": {"$sum": "$total_daily_cost"}}}, {"$sort": {"_id": 1}}]
    return [{"date": x["_id"], "total_daily_cost": round(x["total"], 4)} async for x in db.daily_cost_summary.aggregate(pipeline)]


@router.get("/resources")
async def resources(limit: int = 200) -> list[dict[str, Any]]:
    cursor = db.daily_cost_summary.find({}, {"_id": 0}).sort("total_daily_cost", -1).limit(limit)
    return [x async for x in cursor]


@router.get("/reports/export")
async def export_report(format: str = Query(pattern="^(csv|json|pdf)$"), group_by: str = Query(default="service", pattern="^(service|compartment|resource)$")) -> Response:
    if group_by == "service":
        data = await by_service()
    elif group_by == "compartment":
        data = await by_compartment()
    else:
        data = await by_resource()

    if format == "json":
        return Response(content=json.dumps(data, indent=2), media_type="application/json")
    if format == "csv":
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return PlainTextResponse(output.getvalue(), media_type="text/csv")
    text = "CloudCostLens Report\n\n" + "\n".join(str(x) for x in data)
    return Response(content=text.encode("utf-8"), media_type="application/pdf")
