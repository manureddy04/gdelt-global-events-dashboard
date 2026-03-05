# 🌍 GDELT Analytics Stack

> ClickHouse + Redpanda + FastAPI — production-grade OLAP pipeline for 14 years of GDELT geopolitical data.

---

## Architecture

```
Historical CSV (14 Years)              Daily New Files
        │                                    │
   bulk_loader.py                     producer.py --watch-dir
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
              ┌─────────────────┐
              │    Redpanda     │  ← Kafka-compatible broker
              │  (Topic: gdelt) │
              └────────┬────────┘
                       │ consumer.py (batch insert)
                       ▼
              ┌─────────────────┐
              │   ClickHouse    │  ← OLAP columnar DB
              │  Partitioned    │
              │  by YYYYMM      │
              └────────┬────────┘
                       │
              ┌─────────────────┐
              │   FastAPI       │  → /api/v1/...
              │   Backend       │
              └────────┬────────┘
                       │
              ┌─────────────────┐
              │ React Frontend  │  (your dashboard)
              └─────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Docker Desktop (with Compose v2)
- Python 3.12+
- 8GB+ RAM recommended (ClickHouse is RAM-hungry)

### 2. Clone & Start the Stack

```bash
# Open this workspace in VS Code
code gdelt-stack.code-workspace

# Start all services
docker compose up -d

# Verify everything is healthy
docker compose ps
```

Services will be available at:
| Service            | URL                          |
|--------------------|------------------------------|
| FastAPI docs       | http://localhost:8000/docs   |
| Redpanda Console   | http://localhost:8080        |
| ClickHouse HTTP    | http://localhost:8123        |

### 3. Load Historical Data (one-time)

```bash
cd ingestion/bulk_loader
pip install -r requirements.txt

# Point at your CSV directory
export GDELT_CSV_DIR=/path/to/your/14years/csvs

# Dry run first — lists files without loading
python bulk_loader.py --input-dir $GDELT_CSV_DIR --dry-run

# Real load — 8 parallel workers, auto-resume on restart
python bulk_loader.py --input-dir $GDELT_CSV_DIR --workers 8 --resume
```

**Estimated load time (5000 files, ~1B rows):**
- 4 workers on NVMe: ~2–4 hours
- 8 workers: ~1–2 hours

### 4. Start Daily Streaming (new files)

```bash
cd redpanda
pip install -r requirements.txt

# Watch a directory — produces any new .CSV files to Redpanda
python producer.py --watch-dir /data/gdelt/incoming --poll-interval 300
```

The Consumer runs automatically inside Docker — it reads from Redpanda and batch-inserts to ClickHouse.

---

## 📡 API Reference

### Core Endpoints

```
GET /health                              Health check

GET /api/v1/events/timeseries            Time series aggregation
    ?date_from=2015-01-01
    ?date_to=2018-12-31
    ?country=US
    ?granularity=month

GET /api/v1/events/search                Paginated event search
    ?date_from=...&date_to=...
    ?country=SY&quad_class=4
    ?page=1&limit=100

GET /api/v1/events/top-events           Highest impact events
    ?date_from=...&date_to=...
    ?sort_by=mentions

GET /api/v1/countries/metrics           Per-country KPIs (choropleth)
    ?date_from=...&date_to=...

GET /api/v1/countries/compare           Multi-country comparison
    ?countries=US,CN,RU
    ?date_from=...&date_to=...

GET /api/v1/countries/hotspots          Conflict hotspot countries

GET /api/v1/summary/overview            Dashboard header KPIs

GET /api/v1/summary/ingestion-status    Ingestion health

POST /api/v1/ingest/upload              Upload a CSV via API
POST /api/v1/ingest/trigger-daily       Manually trigger daily watch
```

Full interactive docs at: **http://localhost:8000/docs**

---

## 🗄️ ClickHouse Schema

### Main Table: `gdelt.events`

```sql
PARTITION BY toYYYYMM(event_date)         -- 168 partitions for 14 years
ORDER BY (event_date, action_geo_country, event_code)
```

### Materialized Views (auto-updated)

| View | Purpose |
|------|---------|
| `mv_daily_agg` | Pre-aggregated daily stats per country |
| `mv_country_monthly` | Monthly country summaries for maps |

### Direct ClickHouse Access

```bash
# Via HTTP
curl "http://localhost:8123/?query=SELECT+count(*)+FROM+gdelt.events&user=gdelt_user&password=gdelt_pass"

# Via Docker exec
docker exec -it gdelt_clickhouse clickhouse-client --user gdelt_user --password gdelt_pass
```

---

## 🔧 Configuration

All config via `.env` at project root:

```env
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DB=gdelt
CLICKHOUSE_USER=gdelt_user
CLICKHOUSE_PASSWORD=gdelt_pass

REDPANDA_BROKERS=localhost:19092
REDPANDA_TOPIC=gdelt_events

GDELT_CSV_DIR=/data/gdelt/csv
DAILY_WATCH_DIR=/data/gdelt/incoming

BATCH_SIZE=10000          # consumer batch before CH insert
FLUSH_INTERVAL_SEC=5      # max wait before flushing partial batch
```

---

## 📊 GDELT QuadClass Reference

| Code | Meaning |
|------|---------|
| 1 | Verbal Cooperation |
| 2 | Material Cooperation |
| 3 | Verbal Conflict |
| 4 | Material Conflict |

Goldstein Scale: **-10** (most conflictual) → **+10** (most cooperative)

---

## 🗂️ Project Structure

```
gdelt-stack/
├── docker-compose.yml
├── .env
├── gdelt-stack.code-workspace
│
├── clickhouse/
│   └── schemas/
│       └── 01_init.sql            ← Tables + materialized views
│
├── redpanda/
│   ├── producer.py                ← CSV → Redpanda (daily files)
│   ├── consumer.py                ← Redpanda → ClickHouse
│   ├── requirements.txt
│   └── Dockerfile
│
├── backend/
│   ├── main.py                    ← FastAPI app
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   └── api/v1/
│       ├── router.py
│       └── endpoints/
│           ├── events.py          ← Timeseries, search, top events
│           ├── countries.py       ← Geo metrics, compare, hotspots
│           ├── summary.py         ← Overview KPIs, ingestion status
│           └── ingest.py          ← Upload & trigger ingestion
│
├── ingestion/
│   └── bulk_loader/
│       ├── bulk_loader.py         ← Historical CSV → ClickHouse
│       └── requirements.txt
│
└── docker/
    └── console-config.yaml        ← Redpanda Console config
```

---

## 🛠️ VS Code Integration

The workspace includes pre-configured:
- **Launch configs** — run FastAPI, bulk loader, consumer with F5
- **Tasks** — `Stack Up/Down`, `Bulk Load`, `View Logs` from Task Runner
- **Recommended extensions** — Python, Docker, Thunder Client, SQLTools

---

## ⚡ Performance Tips

- Set `--workers 8` on bulk loader for NVMe SSDs (reduce to 4 for HDD)
- ClickHouse's `max_execution_time=30` prevents runaway queries
- For dashboards, query `gdelt.events_daily_agg` instead of raw `gdelt.events`
- Add `LIMIT` to all queries — ClickHouse can return millions of rows fast but serialization is the bottleneck
