"""
producer.py — FIFA World Cup 2026 Simulated Social Media Ingestion Producer

Simulates a high-volume, bursty social media firehose during live World Cup
matches. Publishes serialized JSON payloads to the Kafka `world_cup_firehose`
topic at variable rates to model real game-day traffic patterns.

Two traffic modes are alternated to stress-test the downstream consumer:
  • NORMAL  — steady stream (group stage pace)
  • SPIKE   — burst mode (goal/penalty/red-card moment)

Usage:
    python producer.py
"""

import json
import time
import random
import signal
import sys
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PRODUCER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Kafka Config ──────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC             = "world_cup_firehose"

# ── Simulated Match Commentary Pool ──────────────────────────────────────────
# Covers multiple teams, players, coaches, and squad nicknames so the entity
# matcher in the consumer has varied real-world-like text to work with.
SAMPLE_POSTS = [
    # USA
    "Pulisic just put the USMNT ahead with a stunning solo run! Incredible!",
    "Balogun holds up the ball brilliantly for the USA, clinical finishing!",
    "USMNT looking shaky in defense, they could be in trouble here.",
    "Christian Pulisic is the heart of this USA squad, incredible vision today.",
    "USA's pressing game is working perfectly, dominating midfield right now.",
    "That was a terrible miss by Folarin Balogun, the USA needed that goal.",
    # Mexico
    "El Tri fighting back! Santi Gimenez with a header, 1-1 now!",
    "Mexico's defensive shape is completely disorganized today, shocking.",
    "Lozano cutting inside — what a goal! El Tri fans are absolutely electric!",
    "Mexico are brilliant on the counter-attack, love watching El Tri play.",
    "Terrible marking from Mexico, they've conceded way too easily tonight.",
    # Canada
    "Alphonso Davies is absolutely unplayable on that left wing for Canada.",
    "CanMNT showing incredible heart, Jonathan David is a star!",
    "Canada are pressing high and it's working, Davies is electric today.",
    "Jonathan David wasted a clear chance for Canada, he'll be disappointed.",
    "CanMNT need to tighten up at the back, too many gaps tonight.",
    # Argentina
    "Messi with the free kick — ARE YOU KIDDING ME?! Albiceleste lead!",
    "Argentina's passing is simply on another level, flawless tonight.",
    "This referee is making horrible decisions against Argentina, unbelievable.",
    "Messi looks like he's playing a different sport, pure genius on display.",
    "The Albiceleste defense is being carved open far too easily here.",
    # Brazil
    "Vinicius Jr leaves three defenders in the dust! Seleção are flying!",
    "Incredible team play from Brazil, Vinicius Jr looks completely unstoppable.",
    "Brasil showing everyone why they are still the favorites, breathtaking.",
    "Brazil's midfield has been overrun in the second half, real concern here.",
    "Rodrygo with a composed finish for Brazil — the crowd goes absolutely wild!",
    # France
    "Mbappé with that acceleration, nobody in the world can catch him — Les Bleus!",
    "France are brilliant in transition, Mbappé and Dembélé combining beautifully.",
    "Les Bleus under real pressure now, their defense is struggling badly.",
    "Mbappé scores again! France are just relentless in attack tonight.",
    # Germany
    "Die Mannschaft showing their trademark organization and discipline tonight.",
    "Germany are clinical in front of goal today, fantastic collective performance.",
    "Die Mannschaft looking vulnerable on set pieces, that's a real weakness.",
    # England
    "The Three Lions are ruthless today! Bellingham pulls the strings perfectly.",
    "England's press is suffocating the opposition, Saka causing constant problems.",
    "England throwing everything forward now, this is end-to-end excitement!",
    # General
    "What an incredible tournament this is, best World Cup in years without doubt!",
    "This referee needs to sort it out, the game is getting out of control.",
    "Absolutely love the atmosphere in this stadium, the fans are incredible!",
    "VAR ruins another moment of joy — the technology needs serious improvement.",
]

# ── Traffic Mode Config ────────────────────────────────────────────────────────
NORMAL_DELAY = (0.3, 0.8)   # seconds between posts during calm phases
SPIKE_DELAY  = (0.02, 0.1)  # seconds between posts during goal/penalty moments

SPIKE_PROBABILITY    = 0.15  # 15% chance each cycle triggers a spike event
SPIKE_DURATION_RANGE = (5, 20)  # spike lasts 5–20 seconds


def create_producer() -> KafkaProducer:
    """Initialize the Kafka producer with retry logic."""
    retries = 0
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                # Async batching — accumulate up to 16 KB or 10 ms before sending
                linger_ms=10,
                batch_size=16384,
                # Retries on transient Kafka errors
                retries=5,
                acks="all",
            )
            log.info("Kafka producer connected to %s", BOOTSTRAP_SERVERS)
            return producer
        except KafkaError as e:
            retries += 1
            wait = min(2 ** retries, 30)
            log.warning("Cannot connect to Kafka (attempt %d): %s. Retrying in %ds…", retries, e, wait)
            time.sleep(wait)


def run():
    producer = create_producer()
    post_id  = 1000
    in_spike = False
    spike_end = 0.0
    published = 0

    log.info("═" * 60)
    log.info("  World Cup 2026 Ingestion Producer — LIVE")
    log.info("  Topic   : %s", TOPIC)
    log.info("  Servers : %s", BOOTSTRAP_SERVERS)
    log.info("═" * 60)

    try:
        while True:
            now = time.time()

            # ── Determine traffic mode ────────────────────────────────────────
            if in_spike and now >= spike_end:
                in_spike = False
                log.info("🏟  Traffic spike ended — returning to normal stream pace")
            elif not in_spike and random.random() < SPIKE_PROBABILITY:
                duration  = random.uniform(*SPIKE_DURATION_RANGE)
                spike_end = now + duration
                in_spike  = True
                log.info("⚡ SPIKE EVENT (goal/penalty moment) — burst mode for %.1fs", duration)

            delay_range = SPIKE_DELAY if in_spike else NORMAL_DELAY

            # ── Build & publish payload ───────────────────────────────────────
            payload = {
                "id":        post_id,
                "text":      random.choice(SAMPLE_POSTS),
                "timestamp": int(now),
                "mode":      "spike" if in_spike else "normal",
            }

            future = producer.send(TOPIC, value=payload)
            future.add_errback(lambda exc: log.error("Delivery failed: %s", exc))

            published += 1
            if published % 50 == 0:
                log.info("📡 %d posts ingested (current mode: %s)", published, payload["mode"])
            else:
                log.debug("Ingested post %d: %s…", post_id, payload["text"][:50])

            post_id += 1
            time.sleep(random.uniform(*delay_range))

    except KeyboardInterrupt:
        log.info("Shutdown signal received — flushing remaining messages…")
        producer.flush(timeout=10)
        producer.close()
        log.info("Producer halted cleanly. Total posts sent: %d", published)
        sys.exit(0)


if __name__ == "__main__":
    run()
