"""
Countries API — for map visualizations and country comparisons.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.database import ch_pool

router = APIRouter()


class CountryMetric(BaseModel):
    country: str
    event_count: int
    avg_goldstein: float
    avg_tone: float
    conflict_count: int
    coop_count: int
    conflict_ratio: float


@router.get("/metrics", response_model=list[CountryMetric])
async def get_country_metrics(
    date_from: date = Query(...),
    date_to:   date = Query(...),
    min_events: int = Query(10, description="Minimum events threshold to filter noise"),
    limit:      int = Query(200, ge=1, le=500),
):
    """
    Per-country aggregated metrics for a time range.
    Ideal for choropleth maps.
    """
    query = """
        SELECT
            action_geo_country              AS country,
            count()                         AS event_count,
            avg(goldstein_scale)            AS avg_goldstein,
            avg(avg_tone)                   AS avg_tone,
            countIf(quad_class >= 3)        AS conflict_count,
            countIf(quad_class <= 2)        AS coop_count
        FROM gdelt.events
        WHERE
            event_date BETWEEN {date_from:Date} AND {date_to:Date}
            AND action_geo_country != ''
        GROUP BY country
        HAVING event_count >= {min_events:UInt32}
        ORDER BY event_count DESC
        LIMIT {limit:UInt32}
        SETTINGS max_execution_time = 30
    """

    try:
        result = ch_pool.query(query, parameters={
            "date_from": str(date_from),
            "date_to": str(date_to),
            "min_events": min_events,
            "limit": limit,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        CountryMetric(
            country=r[0],
            event_count=r[1],
            avg_goldstein=round(r[2], 3),
            avg_tone=round(r[3], 3),
            conflict_count=r[4],
            coop_count=r[5],
            conflict_ratio=round(r[4] / max(r[1], 1), 3),
        )
        for r in result.result_rows
    ]


@router.get("/compare")
async def compare_countries(
    countries:  str  = Query(..., description="Comma-separated ISO codes, e.g. US,CN,RU"),
    date_from:  date = Query(...),
    date_to:    date = Query(...),
    granularity: str = Query("month", description="month | year"),
):
    """
    Side-by-side monthly/yearly metrics for multiple countries.
    Powers multi-line comparison charts.
    """
    country_list = [c.strip().upper() for c in countries.split(",") if c.strip()]
    if len(country_list) > 10:
        raise HTTPException(status_code=400, detail="Max 10 countries per comparison")

    trunc = "toStartOfMonth(event_date)" if granularity == "month" else "toStartOfYear(event_date)"

    query = f"""
        SELECT
            {trunc}                  AS period,
            action_geo_country       AS country,
            count()                  AS event_count,
            avg(goldstein_scale)     AS avg_goldstein,
            avg(avg_tone)            AS avg_tone,
            countIf(quad_class >= 3) AS conflict_count
        FROM gdelt.events
        WHERE
            event_date BETWEEN {{date_from:Date}} AND {{date_to:Date}}
            AND action_geo_country IN ({{countries:Array(String)}})
        GROUP BY period, country
        ORDER BY period, country
        SETTINGS max_execution_time = 30
    """

    try:
        result = ch_pool.query(query, parameters={
            "date_from": str(date_from),
            "date_to": str(date_to),
            "countries": country_list,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    cols = ["period", "country", "event_count", "avg_goldstein", "avg_tone", "conflict_count"]
    return [dict(zip(cols, r)) for r in result.result_rows]


@router.get("/hotspots")
async def get_conflict_hotspots(
    date_from:  date = Query(...),
    date_to:    date = Query(...),
    limit:      int  = Query(20),
):
    """Countries with highest conflict ratio in a time period."""
    query = """
        SELECT
            action_geo_country              AS country,
            count()                         AS total_events,
            countIf(quad_class >= 3)        AS conflict_events,
            round(countIf(quad_class >= 3) / count(), 3) AS conflict_ratio,
            avg(goldstein_scale)            AS avg_goldstein
        FROM gdelt.events
        WHERE
            event_date BETWEEN {date_from:Date} AND {date_to:Date}
            AND action_geo_country != ''
        GROUP BY country
        HAVING total_events > 100
        ORDER BY conflict_ratio DESC
        LIMIT {limit:UInt32}
    """

    try:
        result = ch_pool.query(query, parameters={
            "date_from": str(date_from),
            "date_to": str(date_to),
            "limit": limit,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    cols = ["country", "total_events", "conflict_events", "conflict_ratio", "avg_goldstein"]
    return [dict(zip(cols, r)) for r in result.result_rows]
