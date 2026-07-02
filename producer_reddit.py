"""
producer_reddit.py — FIFA World Cup 2026 Live Reddit Stream Producer

Connects to Reddit's live comment/post streams across multiple soccer
subreddits, filters for World Cup related content, and publishes to the
same `world_cup_firehose` Kafka topic consumed by consumer.py.

Setup (one-time):
    1. Go to https://www.reddit.com/prefs/apps
    2. Click "Create another app..." at the bottom
    3. Choose type: "script"
    4. Name it anything (e.g. "WC2026Tracker")
    5. Set redirect URI to: http://localhost:8080
    6. Copy the client_id (under the app name) and client_secret
    7. Fill in REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT below
       OR set them as environment variables in a .env file

Usage:
    python producer_reddit.py

This replaces producer.py (the simulator) with real live Reddit data.
You can run both simultaneously if you want to mix real + simulated data.
"""

import json
import time
import logging
import sys
import os
import re

import praw
from kafka import KafkaProducer
from kafka.errors import KafkaError
from dotenv import load_dotenv

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [REDDIT] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Reddit API Credentials ────────────────────────────────────────────────────
# Option A: Fill these in directly
# Option B: Set as environment variables or in a .env file (recommended)
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID",     "YOUR_CLIENT_ID_HERE")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT",    "WC2026SentimentTracker/1.0 by YourUsername")

# ── Kafka Config ──────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC             = "world_cup_firehose"

# ── Subreddits to Monitor ─────────────────────────────────────────────────────
# Covers general soccer discourse + nation-specific communities
SUBREDDITS = [
    "soccer",          # Largest general soccer community (~4M members)
    "worldcup",        # Tournament-specific sub
    "FIFA",            # General FIFA discussion
    "usmnt",           # USA fans
    "CanadaSoccer",    # Canada fans
    "LigaMX",          # Mexico fans
    "argentina",       # Argentina fans
    "futebol",         # Brazil fans (Portuguese)
    "soccerstreams",   # Match day discussion threads
    "football",        # Large general football/soccer community
    "MLS",             # US domestic league fans, cross-posts national team news
    "PremierLeague",   # High volume during shared international windows
    "footballhighlights",  # Highlight-reaction traffic
]

# ── World Cup Keyword Filter ──────────────────────────────────────────────────
# Only pass posts/comments that mention World Cup or tracked nations.
# This prevents off-topic content from flooding the pipeline.
WORLD_CUP_KEYWORDS = [
    # Tournament
    "world cup", "worldcup", "wc2026", "worldcup2026", "fifa2026",
    "world cup 2026", "fifaworldcup",
    # USA
    "usmnt", "pulisic", "balogun", "usa soccer", "team usa",
    # Mexico
    "el tri", "mexico", "lozano", "gimenez", "santi gimenez",
    # Canada
    "canmnt", "davies", "alphonso", "jonathan david", "canada soccer",
    # Argentina
    "albiceleste", "messi", "argentina", "scaloneta",
    # Brazil
    "seleção", "selecao", "vinicius", "vinicius jr", "brasil", "brazil",
    # France
    "les bleus", "mbappé", "mbappe", "france football",
    # Germany
    "die mannschaft", "deutschland", "musiala", "kroos",
    # England
    "three lions", "bellingham", "england football", "kane",
    # Spain
    "la roja", "pedri", "gavi", "lamine yamal",
    # Portugal
    "ronaldo", "cristiano", "bruno fernandes", "portugal football",
    # General match terms
    "goal", "penalty", "red card", "offside", "hat trick", "free kick",
    "match thread", "post match", "pre match",
]

KEYWORD_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in WORLD_CUP_KEYWORDS),
    re.IGNORECASE,
)


def is_world_cup_relevant(text: str) -> bool:
    """Return True if the text contains any tracked World Cup keyword."""
    return bool(KEYWORD_PATTERN.search(text))


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


def create_reddit_client() -> praw.Reddit:
    if "YOUR_CLIENT_ID_HERE" in REDDIT_CLIENT_ID:
        log.error("="*60)
        log.error("  Reddit credentials not configured!")
        log.error("  Edit producer_reddit.py and set:")
        log.error("    REDDIT_CLIENT_ID")
        log.error("    REDDIT_CLIENT_SECRET")
        log.error("    REDDIT_USER_AGENT")
        log.error("  Or create a .env file with those variables.")
        log.error("  See setup instructions at the top of this file.")
        log.error("="*60)
        sys.exit(1)

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    log.info("✅ Reddit API client initialized (read-only mode)")
    return reddit


def run():
    kafka_producer = create_kafka_producer()
    reddit         = create_reddit_client()

    # Combine all subreddits into a single multi-stream (PRAW supports this)
    subreddit_str  = "+".join(SUBREDDITS)
    subreddit      = reddit.subreddit(subreddit_str)

    published  = 0
    skipped    = 0
    post_id    = 10000

    log.info("═" * 60)
    log.info("  FIFA World Cup 2026 Reddit Producer — LIVE")
    log.info("  Monitoring: r/%s", subreddit_str[:80] + "…")
    log.info("  Kafka Topic: %s", TOPIC)
    log.info("  Filtering for %d World Cup keywords", len(WORLD_CUP_KEYWORDS))
    log.info("═" * 60)

    try:
        # stream.comments() yields every new comment across all monitored subs
        # in real time — no polling needed, PRAW handles the loop internally
        for comment in subreddit.stream.comments(skip_existing=True):
            text = comment.body.strip()

            # Skip removed/deleted comments
            if text in ("[removed]", "[deleted]", ""):
                continue

            # Filter: only pass World Cup relevant content
            if not is_world_cup_relevant(text):
                skipped += 1
                continue

            payload = {
                "id":          post_id,
                "text":        text[:512],           # cap at model token limit
                "timestamp":   int(comment.created_utc),
                "source":      "reddit",
                "subreddit":   comment.subreddit.display_name,
                "reddit_id":   comment.id,
                "score":       comment.score,        # upvotes (engagement signal)
                "permalink":   f"https://reddit.com{comment.permalink}",
            }

            future = kafka_producer.send(TOPIC, value=payload)
            future.add_errback(lambda exc: log.error("Kafka delivery failed: %s", exc))

            published += 1
            post_id   += 1

            log.info(
                "📨 r/%-15s | %s…",
                comment.subreddit.display_name,
                text[:70].replace("\n", " "),
            )

            if published % 100 == 0:
                log.info(
                    "📊 Stats — Published: %d | Filtered out: %d | Pass rate: %.1f%%",
                    published, skipped,
                    published / max(published + skipped, 1) * 100,
                )

    except KeyboardInterrupt:
        log.info("Shutdown signal — flushing Kafka producer…")
        kafka_producer.flush(timeout=10)
        kafka_producer.close()
        log.info(
            "Reddit producer stopped. Published: %d | Filtered: %d",
            published, skipped,
        )
        sys.exit(0)

    except Exception as e:
        log.error("Unexpected error: %s", e)
        kafka_producer.flush(timeout=5)
        raise


if __name__ == "__main__":
    run()
