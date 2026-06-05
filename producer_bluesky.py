"""
producer_bluesky.py — FIFA World Cup 2026 Live Bluesky Jetstream Stream Producer

Connects to Bluesky's live Jetstream firehose via WebSockets, filters for World Cup
related posts in real-time, and publishes them to the `world_cup_firehose` Kafka topic.

Unlike Reddit, Bluesky is completely open and requires:
    - NO API keys
    - NO account creation / login
    - NO developer application / approvals

Setup:
    - The script automatically installs 'websockets' if it is not present in your environment.

Usage:
    python producer_bluesky.py
"""

import json
import time
import logging
import sys
import os
import re
import asyncio
import subprocess

# ── Dynamic Dependencies ──────────────────────────────────────────────────────
try:
    import websockets
except ImportError:
    logging.warning("'websockets' library not found. Installing it automatically…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets

try:
    from deep_translator import GoogleTranslator
except ImportError:
    logging.warning("'deep-translator' library not found. Installing it automatically…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])
    from deep_translator import GoogleTranslator

from kafka import KafkaProducer
from kafka.errors import KafkaError

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BLUESKY] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Kafka Config ──────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC             = "world_cup_firehose"

# ── Bluesky Jetstream Config ──────────────────────────────────────────────────
# Using the public US-East Jetstream server, filtering for posts (app.bsky.feed.post)
JETSTREAM_URI = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"

# ── World Cup Keyword Filter ──────────────────────────────────────────────────
# Structured as a two-stage filter with exclusion keywords and whole-word matching 
# to reduce non-soccer false positives (e.g., general country mentions, other sports).
import string

HIGHLY_SPECIFIC_KEYWORDS = [
    # Tournament Names
    "world cup", "worldcup", "wc2026", "worldcup2026", "fifa2026", "world cup 2026", "fifaworldcup",
    # Specific Team Nicknames & Associations
    "usmnt", "canmnt", "el tri", "albiceleste", "seleção", "selecao", "three lions", "die mannschaft", "la roja", "les bleus",
    # High-Profile Players
    "pulisic", "balogun", "messi", "vinicius jr", "vinicius", "mbappé", "mbappe", "musiala", "bellingham", "yamal", "lamine yamal",
    "ronaldo", "cristiano", "santi gimenez", "santiago gimenez",
    # Translation Helpers (High precision non-English tournament terms)
    "golaço", "golazo", "copa do mundo", "copa del mundo"
]

CONTEXT_DEPENDENT_KEYWORDS = [
    # Countries (highly generic on their own)
    "usa", "united states", "mexico", "méxico", "canada", "argentina", "brazil", "brasil", "france", "germany", "england", "spain", "portugal",
    # General Match Terms
    "goal", "penalty", "red card", "offside", "hat trick", "free kick", "match thread", "post match", "pre match", "score",
    # Other Players / Coaches (might be generic words)
    "davies", "alphonso", "jonathan david", "lozano", "weah", "aaronson", "berhalter", "turner", "laryea", "herdman",
    "di maria", "de paul", "scaloneta", "scaloni", "rodrygo", "raphinha", "endrick", "neymar", "dembele", "dembélé",
    "griezmann", "giroud", "deschamps", "muller", "müller", "gnabry", "havertz", "kroos", "neuer", "nagelsmann",
    "southgate", "saka", "kane", "harry kane", "foden", "trippier", "rashford", "pedri", "gavi", "morata", "rodri", "olmo",
    "felix", "joao felix", "bruno fernandes", "bernardo silva", "leao", "leão"
]

SOCCER_CONTEXT_WORDS = [
    "soccer", "football", "futbol", "futebol", "match", "matches", "game", "games", "player", "players", "coach", "coaches",
    "referee", "arbitro", "árbitro", "stadium", "copa", "cup", "championship", "squad", "pitch", "vs", "versus", "playoff", "qualifier", "goal",
    "goals", "penalty", "team", "teams", "national team", "liga", "league", "play", "plays", "playing", "played"
]

EXCLUSION_WORDS = [
    "nba", "basketball", "nfl", "nhl", "hockey", "baseball", "mlb", "cricket", "rugby", "tennis", "golf", "volei", "vôlei", "volleyball",
    "xbox", "playstation", "ps5", "fifa 23", "fifa 24", "ea fc", "eafc"
]

def is_world_cup_relevant(text: str) -> bool:
    """Check if the text is relevant using a two-stage specificity filter and whole-word matching."""
    lowered = text.lower()
    
    # 1. Clean words extraction for whole-word checks
    translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
    words = set(lowered.translate(translator).split())
    
    # 2. Check exclusion words immediately (early return)
    for excl in EXCLUSION_WORDS:
        if excl in words:
            return False
            
    # 3. Check highly specific keywords (immediate pass)
    for kw in HIGHLY_SPECIFIC_KEYWORDS:
        if kw in lowered:
            return True
            
    # 4. Check context-dependent keywords
    has_context_keyword = False
    for kw in CONTEXT_DEPENDENT_KEYWORDS:
        if " " in kw:
            if kw in lowered:
                has_context_keyword = True
                break
        else:
            if kw in words:
                has_context_keyword = True
                break
                
    if has_context_keyword:
        # Check if there is soccer context
        for ctx in SOCCER_CONTEXT_WORDS:
            if ctx in words:
                return True
                
    return False

# ── Kafka Producer Initialization ─────────────────────────────────────────────
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

# ── Main Streaming Loop ───────────────────────────────────────────────────────
async def stream_firehose():
    kafka_producer = create_kafka_producer()
    
    published = 0
    skipped = 0
    post_id = 20000  # Start distinct ID range for Bluesky sources

    log.info("═" * 60)
    log.info("  FIFA World Cup 2026 Bluesky Producer — LIVE")
    log.info("  Connecting to Jetstream: %s", JETSTREAM_URI)
    log.info("  Kafka Topic: %s", TOPIC)
    log.info("  Filtering for %d specific / %d context keywords", len(HIGHLY_SPECIFIC_KEYWORDS), len(CONTEXT_DEPENDENT_KEYWORDS))
    log.info("═" * 60)

    # Reconnection loop for WebSocket
    while True:
        try:
            async with websockets.connect(JETSTREAM_URI, ping_interval=20, ping_timeout=20) as ws:
                log.info("📶 Connected to Bluesky Jetstream firehose.")
                
                while True:
                    message = await ws.recv()
                    event = json.loads(message)

                    # Validate Jetstream commit post creation
                    if event.get("kind") != "commit":
                        continue
                    
                    commit = event.get("commit", {})
                    if commit.get("operation") != "create" or commit.get("collection") != "app.bsky.feed.post":
                        continue
                    
                    record = commit.get("record", {})
                    text = record.get("text", "").strip()

                    if not text:
                        continue

                    # Filter for World Cup relevance
                    if not is_world_cup_relevant(text):
                        skipped += 1
                        continue

                    # ── Live Translation Component ──
                    langs = record.get("langs", [])
                    original_text = text
                    translated_text = text
                    is_translated = False
                    
                    try:
                        # Skip translation if language is declared as English
                        is_english = False
                        if langs:
                            is_english = any(l.lower().startswith("en") for l in langs)
                        else:
                            is_english = text.isascii()  # Assume english if it's pure ASCII with no langs array

                        if not is_english:
                            # Run Google translation
                            translated_text = GoogleTranslator(source="auto", target="en").translate(text)
                            if translated_text and translated_text.strip().lower() != text.lower():
                                is_translated = True
                                text = f"{translated_text} [Original: {original_text[:150]}]"
                    except Exception as tx_err:
                        log.warning("Translation failed: %s", tx_err)

                    did = event.get("did", "")
                    rkey = commit.get("rkey", "")
                    time_us = event.get("time_us", 0)
                    timestamp = int(time_us / 1000000) if time_us else int(time.time())

                    # Build standardized payload matching consumer's requirements
                    payload = {
                        "id":          post_id,
                        "text":        text[:512],  # Cap at model token limit
                        "timestamp":   timestamp,
                        "source":      "bluesky",
                        "subreddit":   "Bluesky",   # Reuse field for UI source labeling
                        "reddit_id":   f"{did}_{rkey}"[:50],  # Unique ID mapping
                        "score":       0,
                        "permalink":   f"https://bsky.app/profile/{did}/post/{rkey}",
                    }

                    # Send to Kafka
                    future = kafka_producer.send(TOPIC, value=payload)
                    future.add_errback(lambda exc: log.error("Kafka delivery failed: %s", exc))

                    published += 1
                    post_id += 1

                    if is_translated:
                        log.info(
                            "🌐 [BSKY TR] | %s…",
                            translated_text[:70].replace("\n", " "),
                        )
                    else:
                        log.info(
                            "📨 [BSKY] | %s…",
                            original_text[:70].replace("\n", " "),
                        )

                    if published % 50 == 0:
                        log.info(
                            "📊 Stats — Published: %d | Filtered out: %d | Pass rate: %.1f%%",
                            published, skipped,
                            published / max(published + skipped, 1) * 100,
                        )

        except websockets.exceptions.ConnectionClosed as e:
            log.warning("Connection closed: %s. Reconnecting in 5 seconds…", e)
            await asyncio.sleep(5)
        except Exception as e:
            log.error("Error in streaming loop: %s. Reconnecting in 5 seconds…", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(stream_firehose())
    except KeyboardInterrupt:
        log.info("Shutdown signal — exiting.")
        sys.exit(0)
