"""
producer_twitter.py — FIFA World Cup 2026 X (Twitter) Filtered Stream Producer

Publishes matching posts from X's v2 filtered stream to the same
`world_cup_firehose` Kafka topic consumed by consumer.py.

⚠️ COST NOTE — read before running:
    X removed free filtered-stream access in 2023. As of writing, the
    filtered stream endpoint requires at minimum the paid "Basic" API tier
    (~$200/month billed to a developer account), not the free tier. There is
    no way around this with an official, ToS-compliant integration — if you
    don't have a paid tier, this script will fail on rule creation with a
    403. This file is provided so you can wire it in the moment you have
    access; it isn't useful without a paid bearer token.

Setup (one-time):
    1. Apply for a developer account at https://developer.x.com
    2. Subscribe to at least the Basic tier (filtered stream requirement)
    3. Generate a Bearer Token for your app
    4. Set it as X_BEARER_TOKEN below, as an env var, or in a .env file

Usage:
    python producer_twitter.py
"""

import json
import time
import logging
import sys
import os

import requests
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import KafkaError

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [X/TWITTER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "YOUR_BEARER_TOKEN_HERE")
BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC = "world_cup_firehose"

STREAM_RULES_URL = "https://api.x.com/2/tweets/search/stream/rules"
STREAM_URL = (
    "https://api.x.com/2/tweets/search/stream"
    "?tweet.fields=created_at,lang,public_metrics"
    "&expansions=author_id"
)

# Filtered-stream rules — same nations/players as the other producers.
# X rules max out at 512 chars each and 25 rules on Basic tier, so these
# are grouped rather than one keyword per rule.
STREAM_RULES = [
    {"value": '"world cup" OR worldcup2026 OR fifaworldcup lang:en', "tag": "tournament"},
    {"value": "usmnt OR pulisic OR balogun lang:en", "tag": "usa"},
    {"value": '"el tri" OR gimenez OR lozano lang:en', "tag": "mexico"},
    {"value": "canmnt OR davies OR \"jonathan david\" lang:en", "tag": "canada"},
    {"value": "messi OR albiceleste OR scaloni lang:en", "tag": "argentina"},
    {"value": "seleção OR selecao OR vinicius OR neymar", "tag": "brazil"},
    {"value": '"les bleus" OR mbappe OR mbappé lang:en', "tag": "france"},
    {"value": '"three lions" OR bellingham OR harry kane lang:en', "tag": "england"},
]


def create_kafka_producer() -> KafkaProducer:
    retries = 0
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                linger_ms=10,
                batch_size=16384,
                retries=5,
                acks="all",
            )
            log.info("✅ Kafka producer connected to %s", BOOTSTRAP_SERVERS)
            return producer
        except KafkaError as e:
            retries += 1
            wait = min(2 ** retries, 30)
            log.warning("Kafka unavailable (attempt %d): %s. Retrying in %ds…", retries, e, wait)
            time.sleep(wait)


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {X_BEARER_TOKEN}"}


def check_credentials():
    if "YOUR_BEARER_TOKEN_HERE" in X_BEARER_TOKEN:
        log.error("=" * 60)
        log.error("  X bearer token not configured!")
        log.error("  Set X_BEARER_TOKEN as an env var or in a .env file.")
        log.error("  Filtered stream also requires a PAID API tier (Basic+).")
        log.error("  See setup instructions at the top of this file.")
        log.error("=" * 60)
        sys.exit(1)


def sync_stream_rules():
    """Replace any existing stream rules with STREAM_RULES."""
    resp = requests.get(STREAM_RULES_URL, headers=_auth_headers(), timeout=15)
    resp.raise_for_status()
    existing = resp.json().get("data", [])
    if existing:
        ids = [r["id"] for r in existing]
        requests.post(
            STREAM_RULES_URL,
            headers=_auth_headers(),
            json={"delete": {"ids": ids}},
            timeout=15,
        ).raise_for_status()
        log.info("Removed %d stale stream rule(s)", len(ids))

    resp = requests.post(
        STREAM_RULES_URL,
        headers=_auth_headers(),
        json={"add": STREAM_RULES},
        timeout=15,
    )
    if resp.status_code == 403:
        log.error("403 creating stream rules — your API tier likely doesn't include filtered stream access.")
        sys.exit(1)
    resp.raise_for_status()
    log.info("✅ Registered %d stream rule(s)", len(STREAM_RULES))


def run():
    check_credentials()
    kafka_producer = create_kafka_producer()
    sync_stream_rules()

    post_id = 40000  # distinct ID range for X/Twitter sources
    published = 0

    log.info("═" * 60)
    log.info("  FIFA World Cup 2026 X (Twitter) Producer — LIVE")
    log.info("  Kafka Topic: %s", TOPIC)
    log.info("═" * 60)

    backoff = 1
    while True:
        try:
            with requests.get(STREAM_URL, headers=_auth_headers(), stream=True, timeout=90) as resp:
                if resp.status_code != 200:
                    log.warning("Stream connect failed (%d): %s", resp.status_code, resp.text[:200])
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue

                backoff = 1
                log.info("📶 Connected to X filtered stream.")

                for line in resp.iter_lines():
                    if not line:
                        continue  # keep-alive newline
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    tweet = event.get("data", {})
                    text = tweet.get("text", "").strip()
                    if not text:
                        continue

                    metrics = tweet.get("public_metrics", {})
                    payload = {
                        "id": post_id,
                        "text": text[:512],
                        "timestamp": int(time.time()),
                        "source": "twitter",
                        "subreddit": "X",  # reuse field for UI source labeling
                        "reddit_id": tweet.get("id", "")[:50],
                        "score": int(metrics.get("like_count", 0)),
                        "permalink": f"https://x.com/i/web/status/{tweet.get('id', '')}",
                    }

                    future = kafka_producer.send(TOPIC, value=payload)
                    future.add_errback(lambda exc: log.error("Kafka delivery failed: %s", exc))

                    published += 1
                    post_id += 1

                    log.info("📨 [X] %s…", text[:70].replace("\n", " "))
                    if published % 100 == 0:
                        log.info("📊 Stats — Published: %d", published)

        except requests.exceptions.RequestException as e:
            log.warning("Stream error: %s. Reconnecting in %ds…", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except KeyboardInterrupt:
            log.info("Shutdown signal — flushing Kafka producer…")
            kafka_producer.flush(timeout=10)
            kafka_producer.close()
            log.info("X producer stopped. Published: %d", published)
            sys.exit(0)


if __name__ == "__main__":
    run()
