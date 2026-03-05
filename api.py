from fastapi import FastAPI
import clickhouse_connect

app = FastAPI()

client = clickhouse_connect.get_client(
    host="localhost",
    port=8123,
    username="gdelt_user",
    password="gdelt_pass",
    database="gdelt"
)

@app.get("/")
def home():
    return {"status": "GDELT API running"}

@app.get("/count")
def get_count():
    result = client.query("SELECT count() FROM events")
    return {"event_count": result.result_rows[0][0]}
@app.get("/top-countries/{year}")
def top_countries(year: int):
    result = client.query(f"""
        SELECT country, total_events
        FROM country_year_stats
        WHERE year = {year}
        ORDER BY total_events DESC
        LIMIT 10
    """)
    return result.result_rows

@app.get("/global-conflict-trend")
def global_conflict_trend():
    result = client.query("""
        SELECT
            year,
            avg(goldstein_scale) AS avg_conflict
        FROM gdelt.events
        GROUP BY year
        ORDER BY year
    """)
    return result.result_rows

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/sample-events")
def sample_events():
    result = client.query("""
        SELECT
            action_geo_lat,
            action_geo_long,
            actor1_country,
            goldstein_scale
        FROM gdelt.events
        WHERE action_geo_lat != 0
        LIMIT 500
    """)
    
    return [
        {
            "lat": row[0],
            "lon": row[1],
            "country": row[2],
            "goldstein": row[3]
        }
        for row in result.result_rows
    ]

@app.get("/events-by-year")
def events_by_year(year: int):
    result = client.query(f"""
        SELECT
            action_geo_lat,
            action_geo_long,
            actor1_country,
            goldstein_scale
        FROM gdelt.events
        WHERE year = {year}
        AND action_geo_lat != 0
        LIMIT 2000
    """)

    return [
        {
            "lat": row[0],
            "lon": row[1],
            "country": row[2] if row[2] else "Unknown",
            "goldstein": row[3],
        }
        for row in result.result_rows
    ]

import time

@app.get("/response-time-test")
def response_time_test():
    start_time = time.time()

    result = client.query("SELECT count() FROM gdelt.events")

    end_time = time.time()

    response_time = end_time - start_time

    return {
        "response_time_seconds": round(response_time, 5),
        "count": result.result_rows[0][0]
    }