-- ============================================================
-- GDELT Events Table — Primary Store
-- ============================================================
-- Run order: this file is auto-loaded by ClickHouse on startup
-- via docker-entrypoint-initdb.d

CREATE DATABASE IF NOT EXISTS gdelt;

-- ─────────────────────────────────────────────────────────────
-- 1. Main Events Table
--    Partitioned by month  → skips irrelevant months instantly
--    Ordered by date+country → fast WHERE clause filtering
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gdelt.events
(
    -- Core temporal
    event_date          Date,
    event_year          UInt16,
    event_month         UInt8,

    -- Event identity
    global_event_id     UInt64,
    event_code          String,
    event_base_code     String,
    event_root_code     String,

    -- Actor 1
    actor1_code         String,
    actor1_name         String,
    actor1_country      String,
    actor1_type1_code   String,

    -- Actor 2
    actor2_code         String,
    actor2_name         String,
    actor2_country      String,
    actor2_type1_code   String,

    -- Geo
    action_geo_type     UInt8,
    action_geo_fullname String,
    action_geo_country  String,
    action_geo_lat      Float32,
    action_geo_long     Float32,

    -- Metrics
    is_root_event       UInt8,
    quad_class          UInt8,         -- 1=Verbal Coop, 2=Material Coop, 3=Verbal Conflict, 4=Material Conflict
    goldstein_scale     Float32,       -- -10 to +10, impact score
    num_mentions        UInt32,
    num_sources         UInt32,
    num_articles        UInt32,
    avg_tone            Float32,

    -- Source
    source_url          String,
    ingest_ts           DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)           -- Monthly partitions (168 partitions for 14 years)
ORDER BY (event_date, action_geo_country, event_code)
SETTINGS
    index_granularity = 8192,
    merge_with_ttl_timeout = 3600;


-- ─────────────────────────────────────────────────────────────
-- 2. Daily Aggregation — Materialized View
--    Pre-computed so dashboard queries are instant
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gdelt.events_daily_agg
(
    event_date      Date,
    country         String,
    event_root_code String,
    quad_class      UInt8,
    event_count     UInt64,
    avg_goldstein   Float64,
    avg_tone        Float64,
    total_mentions  UInt64
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, country, event_root_code, quad_class);

CREATE MATERIALIZED VIEW IF NOT EXISTS gdelt.mv_daily_agg
TO gdelt.events_daily_agg
AS
SELECT
    event_date,
    action_geo_country  AS country,
    event_root_code,
    quad_class,
    count()             AS event_count,
    avg(goldstein_scale) AS avg_goldstein,
    avg(avg_tone)       AS avg_tone,
    sum(num_mentions)   AS total_mentions
FROM gdelt.events
GROUP BY event_date, country, event_root_code, quad_class;


-- ─────────────────────────────────────────────────────────────
-- 3. Country Monthly Summary — for fast map/chart rendering
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gdelt.country_monthly_summary
(
    year_month      UInt32,   -- YYYYMM
    country         String,
    event_count     UInt64,
    avg_goldstein   Float64,
    avg_tone        Float64,
    conflict_count  UInt64,
    coop_count      UInt64
)
ENGINE = SummingMergeTree()
ORDER BY (year_month, country);

CREATE MATERIALIZED VIEW IF NOT EXISTS gdelt.mv_country_monthly
TO gdelt.country_monthly_summary
AS
SELECT
    toYYYYMM(event_date)        AS year_month,
    action_geo_country          AS country,
    count()                     AS event_count,
    avg(goldstein_scale)        AS avg_goldstein,
    avg(avg_tone)               AS avg_tone,
    countIf(quad_class >= 3)    AS conflict_count,
    countIf(quad_class <= 2)    AS coop_count
FROM gdelt.events
GROUP BY year_month, country;


-- ─────────────────────────────────────────────────────────────
-- 4. Ingestion Log — track what files have been loaded
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gdelt.ingestion_log
(
    file_name       String,
    file_date       Date,
    rows_inserted   UInt64,
    ingested_at     DateTime DEFAULT now(),
    source          Enum8('bulk'=1, 'stream'=2),
    status          Enum8('success'=1, 'failed'=2)
)
ENGINE = MergeTree()
ORDER BY (ingested_at, file_name);
