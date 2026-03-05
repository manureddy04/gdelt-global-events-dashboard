#!/usr/bin/env python3
"""
GDELT Daily CSV Producer
=========================
Watches a directory (or S3 bucket) for new GDELT files and streams
them into Redpanda as JSON events.

Usage:
    python producer.py --watch-dir /data/gdelt/incoming
    python producer.py --file /data/gdelt/incoming/20240115.export.CSV
    python producer.py --watch-dir /data/gdelt/incoming --poll-interval 300
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime

from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

BROKERS = os.getenv("REDPANDA_BROKERS", "localhost:19092")
TOPIC   = os.getenv("REDPANDA_TOPIC", "gdelt_events")

# GDELT column → message field name mapping
COLUMN_MAP = {
    "DATEADDED": "event_date",
    "GlobalEventID": "global_event_id",
    "EventCode": "event_code",
    "EventBaseCode": "event_base_code",
    "EventRootCode": "event_root_code",
    "Actor1Code": "actor1_code",
    "Actor1Name": "actor1_name",
    "Actor1CountryCode": "actor1_country",
    "Actor1Type1Code": "actor1_type1_code",
    "Actor2Code": "actor2_code",
    "Actor2Name": "actor2_name",
    "Actor2CountryCode": "actor2_country",
    "Actor2Type1Code": "actor2_type1_code",
    "ActionGeo_Type": "action_geo_type",
    "ActionGeo_FullName": "action_geo_fullname",
    "ActionGeo_CountryCode": "action_geo_country",
    "ActionGeo_Lat": "action_geo_lat",
    "ActionGeo_Long": "action_geo_long",
    "IsRootEvent": "is_root_event",
    "QuadClass": "quad_class",
    "GoldsteinScale": "goldstein_scale",
    "NumMentions": "num_mentions",
    "NumSources": "num_sources",
    "NumArticles": "num_articles",
    "AvgTone": "avg_tone",
    "SOURCEURL": "source_url",
}


def ensure_topic_exists(brokers: str, topic: str, partitions: int = 6):
    """Create topic if it doesn't exist."""
    admin = AdminClient({"bootstrap.servers": brokers})
    existing = admin.list_topics(timeout=10).topics
    if topic not in existing:
        log.info(f"Creating topic '{topic}' with {partitions} partitions...")
        admin.create_topics([NewTopic(topic, num_partitions=partitions, replication_factor=1)])
        time.sleep(2)  # let Redpanda settle
        log.info("Topic created.")


def delivery_report(err, msg):
    if err:
        log.error(f"Message delivery failed: {err}")


def produce_file(producer: Producer, filepath: Path) -> int:
    """Stream a CSV file's rows as JSON messages to Redpanda."""
    rows_sent = 0
    filename = filepath.name

    log.info(f"Producing: {filename}")
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # Remap columns
                payload = {
                    target: row.get(source, "")
                    for source, target in COLUMN_MAP.items()
                }
                payload["_source_file"] = filename

                # Use event_date as partition key for ordering
                key = payload.get("event_date", "")[:8]

                producer.produce(
                    topic=TOPIC,
                    key=key.encode("utf-8"),
                    value=json.dumps(payload).encode("utf-8"),
                    on_delivery=delivery_report,
                )
                rows_sent += 1

                # Poll to handle delivery callbacks and avoid buffer overflow
                if rows_sent % 10_000 == 0:
                    producer.poll(0)
                    log.info(f"  {rows_sent:,} rows queued from {filename}")

        producer.flush()
        log.info(f"✅ {filename}: {rows_sent:,} rows produced")
        return rows_sent

    except Exception as e:
        log.error(f"❌ Failed producing {filename}: {e}")
        return 0


def watch_directory(producer: Producer, watch_dir: Path, poll_interval: int, processed_log: Path):
    """Poll a directory for new CSV files and produce them."""
    already_processed = set()
    if processed_log.exists():
        already_processed = set(processed_log.read_text().splitlines())
    log.info(f"Watching {watch_dir} every {poll_interval}s. {len(already_processed)} files already done.")

    while True:
        try:
            csv_files = sorted(watch_dir.glob("*.CSV")) + sorted(watch_dir.glob("*.csv"))
            new_files = [f for f in csv_files if f.name not in already_processed]

            if new_files:
                log.info(f"Found {len(new_files)} new file(s)")
                for filepath in new_files:
                    rows = produce_file(producer, filepath)
                    if rows > 0:
                        already_processed.add(filepath.name)
                        with open(processed_log, "a") as lf:
                            lf.write(filepath.name + "\n")
            else:
                log.debug("No new files found.")

        except Exception as e:
            log.error(f"Watch loop error: {e}")

        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="GDELT Daily CSV Producer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file",      type=Path, help="Produce a single CSV file")
    group.add_argument("--watch-dir", type=Path, help="Watch directory for new files")
    parser.add_argument("--poll-interval", type=int, default=300, help="Watch poll interval in seconds (default: 300)")
    parser.add_argument("--processed-log", type=Path, default=Path(".produced_files.txt"),
                        help="File tracking already-produced files")
    args = parser.parse_args()

    ensure_topic_exists(BROKERS, TOPIC)

    producer = Producer({
        "bootstrap.servers": BROKERS,
        "queue.buffering.max.messages": 500_000,
        "queue.buffering.max.kbytes": 512_000,
        "batch.num.messages": 10_000,
        "linger.ms": 50,
        "compression.type": "snappy",
        "acks": "1",
    })

    if args.file:
        if not args.file.exists():
            log.error(f"File not found: {args.file}")
            sys.exit(1)
        produce_file(producer, args.file)
    else:
        if not args.watch_dir.exists():
            log.error(f"Watch directory not found: {args.watch_dir}")
            sys.exit(1)
        watch_directory(producer, args.watch_dir, args.poll_interval, args.processed_log)


if __name__ == "__main__":
    main()
