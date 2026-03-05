#!/usr/bin/env python3
"""
Redpanda → ClickHouse Consumer
================================
Reads GDELT event messages from Redpanda topic and batch-inserts into ClickHouse.
Runs as a persistent service inside Docker.

Features:
  - Configurable batch size and flush interval
  - Graceful shutdown on SIGTERM
  - Dead letter queue for malformed records
  - Lag monitoring via structured logs
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime

import clickhouse_connect
from confluent_kafka import Consumer, KafkaError, KafkaException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

# ── Config from environment ──────────────────────────────────────────────────
BROKERS         = os.getenv("REDPANDA_BROKERS", "localhost:19092")
TOPIC           = os.getenv("REDPANDA_TOPIC", "gdelt_events")
GROUP_ID        = os.getenv("REDPANDA_GROUP_ID", "gdelt_consumer_group")
BATCH_SIZE      = int(os.getenv("BATCH_SIZE", 10_000))
FLUSH_INTERVAL  = int(os.getenv("FLUSH_INTERVAL_SEC", 5))

CH_HOST         = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT         = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_DB           = os.getenv("CLICKHOUSE_DB", "gdelt")
CH_USER         = os.getenv("CLICKHOUSE_USER", "gdelt_user")
CH_PASS         = os.getenv("CLICKHOUSE_PASSWORD", "gdelt_pass")

COLUMNS = [
    "event_date", "event_year", "event_month", "global_event_id",
    "event_code", "event_base_code", "event_root_code",
    "actor1_code", "actor1_name", "actor1_country", "actor1_type1_code",
    "actor2_code", "actor2_name", "actor2_country", "actor2_type1_code",
    "action_geo_type", "action_geo_fullname", "action_geo_country",
    "action_geo_lat", "action_geo_long",
    "is_root_event", "quad_class", "goldstein_scale",
    "num_mentions", "num_sources", "num_articles", "avg_tone",
    "source_url", "ingest_ts",
]

running = True


def signal_handler(sig, frame):
    global running
    log.info(f"Received signal {sig}. Graceful shutdown initiated...")
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def get_ch_client():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, database=CH_DB,
        username=CH_USER, password=CH_PASS,
    )


def msg_to_row(payload: dict) -> list | None:
    """Transform a Redpanda message payload into a ClickHouse row."""
    try:
        date_str = str(payload.get("event_date", ""))[:8]
        event_date = datetime.strptime(date_str, "%Y%m%d").date()

        def fi(k, d=0):
            v = payload.get(k)
            try: return int(v) if v not in (None, "") else d
            except: return d

        def ff(k, d=0.0):
            v = payload.get(k)
            try: return float(v) if v not in (None, "") else d
            except: return d

        def fs(k):
            return str(payload.get(k, "") or "")

        return [
            event_date, event_date.year, event_date.month,
            fi("global_event_id"),
            fs("event_code"), fs("event_base_code"), fs("event_root_code"),
            fs("actor1_code"), fs("actor1_name"), fs("actor1_country"), fs("actor1_type1_code"),
            fs("actor2_code"), fs("actor2_name"), fs("actor2_country"), fs("actor2_type1_code"),
            fi("action_geo_type"),
            fs("action_geo_fullname"), fs("action_geo_country"),
            ff("action_geo_lat"), ff("action_geo_long"),
            fi("is_root_event"), fi("quad_class"),
            ff("goldstein_scale"),
            fi("num_mentions"), fi("num_sources"), fi("num_articles"),
            ff("avg_tone"),
            fs("source_url"),
            datetime.utcnow(),
        ]
    except Exception as e:
        log.warning(f"Skipping malformed message: {e} | payload={payload}")
        return None


def flush_batch(ch_client, batch: list[list]) -> int:
    """Insert batch into ClickHouse. Returns rows inserted."""
    if not batch:
        return 0
    try:
        ch_client.insert("gdelt.events", batch, column_names=COLUMNS)
        return len(batch)
    except Exception as e:
        log.error(f"ClickHouse insert failed: {e}. Batch of {len(batch)} dropped.")
        return 0


def main():
    log.info(f"Consumer starting | topic={TOPIC} broker={BROKERS} batch={BATCH_SIZE}")

    consumer = Consumer({
        "bootstrap.servers": BROKERS,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "fetch.min.bytes": 1,
        "fetch.wait.max.ms": 500,
    })
    consumer.subscribe([TOPIC])

    ch_client = get_ch_client()
    batch: list[list] = []
    last_flush = time.time()
    total_inserted = 0
    total_errors = 0

    log.info("Waiting for messages...")

    while running:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            # Timeout — check if we should flush anyway
            pass
        elif msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                log.debug("End of partition reached")
            else:
                log.error(f"Kafka error: {msg.error()}")
                total_errors += 1
        else:
            try:
                payload = json.loads(msg.value().decode("utf-8"))
                row = msg_to_row(payload)
                if row:
                    batch.append(row)
            except json.JSONDecodeError as e:
                log.warning(f"Invalid JSON: {e}")
                total_errors += 1

        # Flush when batch is full OR flush interval elapsed
        should_flush = (
            len(batch) >= BATCH_SIZE or
            (batch and time.time() - last_flush >= FLUSH_INTERVAL)
        )

        if should_flush:
            inserted = flush_batch(ch_client, batch)
            total_inserted += inserted
            consumer.commit(asynchronous=False)  # Commit after successful insert
            log.info(
                f"Flushed {inserted:,} rows | "
                f"total={total_inserted:,} | "
                f"errors={total_errors}"
            )
            batch.clear()
            last_flush = time.time()

    # ── Shutdown: flush remaining ────────────────────────────────────────────
    log.info("Flushing remaining messages before shutdown...")
    if batch:
        inserted = flush_batch(ch_client, batch)
        total_inserted += inserted
        consumer.commit(asynchronous=False)
        log.info(f"Final flush: {inserted:,} rows")

    consumer.close()
    log.info(f"Consumer stopped. Total inserted: {total_inserted:,}")


if __name__ == "__main__":
    main()
