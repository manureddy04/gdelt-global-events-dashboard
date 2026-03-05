"""
Events API endpoints
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.database import ch_pool
from core.config import settings

router = APIRouter()


# ── Response Models ──────────────────────────────────────────────────────────

class TimeSeriesPoint(BaseModel):
    event_date: date
    event_count: int
    avg_goldstein: float
    avg_tone: float


class EventRecord(BaseModel):
    event_date: date
    global_event_id: int
    event_code: str
    actor1_name: str
    actor2_name: str
    action_geo_country: str
    goldstein_scale: float
    avg_tone: float
    num_articles: int
    source_url: str


class TimeSeriesResponse(BaseModel):
    data: list[TimeSeriesPoint]
    total_records: int
    date_from: str
    date_to: str
    query_ms: float


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/timeseries", response_model=TimeSeriesResponse)
async def get_timeseries(
    date_from: date = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to:   date = Query(..., description="End date (YYYY-MM-DD)"),
    country:   Optional[str] = Query(None, description="ISO country code filter, e.g. US"),
    event_root_code: Optional[str] = Query(None, description="CAMEO root code, e.g. 14 (protest)"),
    granularity: str = Query("day", description="Aggregation: day | month | year"),
):
    """
    Return aggregated event counts and metrics over time.
    Powers line charts on the dashboard.

    Example: GET /api/v1/events/timeseries?date_from=2015-01-01&date_to=2018-12-31&country=US
    """
    if (date_to - date_from).days > 365 * 5 and granularity == "day":
        granularity = "month"  # Auto-upgrade to avoid massive result sets

    granularity_map = {
        "day":   "event_date",
        "month": "toStartOfMonth(event_date)",
        "year":  "toStartOfYear(event_date)",
    }
    trunc_expr = granularity_map.get(granularity, "event_date")

    where_clauses = ["event_date BETWEEN {date_from:Date} AND {date_to:Date}"]
    params = {"date_from": str(date_from), "date_to": str(date_to)}

    if country:
        where_clauses.append("action_geo_country = {country:String}")
        params["country"] = country.upper()

    if event_root_code:
        where_clauses.append("event_root_code = {event_root_code:String}")
        params["event_root_code"] = event_root_code

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            {trunc_expr}        AS period,
            count()             AS event_count,
            avg(goldstein_scale) AS avg_goldstein,
            avg(avg_tone)       AS avg_tone
        FROM gdelt.events
        WHERE {where_sql}
        GROUP BY period
        ORDER BY period
        SETTINGS max_execution_time = 30
    """

    import time
    t0 = time.time()
    try:
        result = ch_pool.query(query, parameters=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {e}")
    query_ms = (time.time() - t0) * 1000

    data = [
        TimeSeriesPoint(
            event_date=row[0],
            event_count=row[1],
            avg_goldstein=round(row[2], 3),
            avg_tone=round(row[3], 3),
        )
        for row in result.result_rows
    ]

    return TimeSeriesResponse(
        data=data,
        total_records=len(data),
        date_from=str(date_from),
        date_to=str(date_to),
        query_ms=round(query_ms, 1),
    )


@router.get("/search", response_model=list[EventRecord])
async def search_events(
    date_from: date = Query(...),
    date_to:   date = Query(...),
    country:   Optional[str] = Query(None),
    actor_name: Optional[str] = Query(None, description="Partial match on actor1 or actor2 name"),
    event_code: Optional[str] = Query(None),
    quad_class: Optional[int] = Query(None, description="1=VerbCoop 2=MatCoop 3=VerbConflict 4=MatConflict"),
    min_goldstein: Optional[float] = Query(None),
    max_goldstein: Optional[float] = Query(None),
    page:  int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=10_000),
):
    """
    Paginated event search with multiple filter dimensions.
    """
    where_clauses = ["event_date BETWEEN {date_from:Date} AND {date_to:Date}"]
    params: dict = {"date_from": str(date_from), "date_to": str(date_to)}

    if country:
        where_clauses.append("action_geo_country = {country:String}")
        params["country"] = country.upper()

    if event_code:
        where_clauses.append("event_code = {event_code:String}")
        params["event_code"] = event_code

    if quad_class is not None:
        where_clauses.append("quad_class = {quad_class:UInt8}")
        params["quad_class"] = quad_class

    if min_goldstein is not None:
        where_clauses.append("goldstein_scale >= {min_gs:Float32}")
        params["min_gs"] = min_goldstein

    if max_goldstein is not None:
        where_clauses.append("goldstein_scale <= {max_gs:Float32}")
        params["max_gs"] = max_goldstein

    if actor_name:
        # ClickHouse ILIKE-equivalent
        where_clauses.append("(actor1_name ILIKE {actor:String} OR actor2_name ILIKE {actor:String})")
        params["actor"] = f"%{actor_name}%"

    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    query = f"""
        SELECT
            event_date, global_event_id, event_code,
            actor1_name, actor2_name,
            action_geo_country, goldstein_scale, avg_tone,
            num_articles, source_url
        FROM gdelt.events
        WHERE {where_sql}
        ORDER BY event_date DESC, num_articles DESC
        LIMIT {{limit:UInt32}} OFFSET {{offset:UInt32}}
        SETTINGS max_execution_time = 30
    """

    try:
        result = ch_pool.query(query, parameters=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        EventRecord(
            event_date=r[0], global_event_id=r[1], event_code=r[2],
            actor1_name=r[3], actor2_name=r[4], action_geo_country=r[5],
            goldstein_scale=r[6], avg_tone=r[7], num_articles=r[8], source_url=r[9],
        )
        for r in result.result_rows
    ]


@router.get("/top-events")
async def get_top_events(
    date_from: date = Query(...),
    date_to:   date = Query(...),
    country:   Optional[str] = Query(None),
    limit:     int  = Query(20, ge=1, le=200),
    sort_by:   str  = Query("mentions", description="mentions | articles | goldstein"),
):
    """Return highest-impact events in a time range."""
    sort_map = {
        "mentions":  "num_mentions DESC",
        "articles":  "num_articles DESC",
        "goldstein": "abs(goldstein_scale) DESC",
    }
    order = sort_map.get(sort_by, "num_mentions DESC")

    params = {"date_from": str(date_from), "date_to": str(date_to), "limit": limit}
    where = "event_date BETWEEN {date_from:Date} AND {date_to:Date}"
    if country:
        where += " AND action_geo_country = {country:String}"
        params["country"] = country.upper()

    query = f"""
        SELECT
            event_date, global_event_id, event_code,
            actor1_name, actor2_name, action_geo_fullname,
            goldstein_scale, avg_tone, num_mentions, num_articles, source_url
        FROM gdelt.events
        WHERE {where}
        ORDER BY {order}
        LIMIT {{limit:UInt32}}
        SETTINGS max_execution_time = 30
    """

    try:
        result = ch_pool.query(query, parameters=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    cols = ["event_date","global_event_id","event_code","actor1_name","actor2_name",
            "action_geo_fullname","goldstein_scale","avg_tone","num_mentions","num_articles","source_url"]
    return [dict(zip(cols, r)) for r in result.result_rows]
