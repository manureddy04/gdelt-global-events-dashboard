"""
GDELT Analytics API
====================
FastAPI backend serving ClickHouse query results.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.router import api_router
from core.config import settings
from core.database import ch_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 GDELT API starting — ClickHouse @ {settings.CLICKHOUSE_HOST}")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="GDELT Analytics API",
    version="1.0.0",
    description="Query 14 years of GDELT geopolitical event data via ClickHouse",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check — also pings ClickHouse."""
    try:
        result = ch_pool.query("SELECT 1")
        ch_ok = result.result_rows == [(1,)]
    except Exception as e:
        return {"status": "degraded", "clickhouse": str(e)}
    return {"status": "ok", "clickhouse": "connected"}

@app.get("/events")
def get_events(year: int = None, month: int = None, day: int = None):

    query = """
    SELECT
        action_geo_lat,
        action_geo_long,
        goldstein_scale,
        actor1_country,
        sql_date
    FROM events
    WHERE 1=1
    """

    if year:
        query += f" AND toYear(toDate(toString(sql_date))) = {year}"

    if month:
        query += f" AND toMonth(toDate(toString(sql_date))) = {month}"

    if day:
        query += f" AND toDayOfMonth(toDate(toString(sql_date))) = {day}"

    query += " LIMIT 5000"

    data = client.query(query).result_rows

    return [
        {
            "lat": r[0],
            "lon": r[1],
            "tone": r[2],
            "country": r[3],
            "date": r[4]
        }
        for r in data
    ]