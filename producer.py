"""
<<<<<<< HEAD
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

=======
producer.py — FIFA World Cup 2026 Real YouTube Ingestion Producer

Publishes real YouTube live-chat messages and recent video comments to the
Kafka `world_cup_firehose` topic consumed by consumer.py.

Data source behavior:
  1. If YOUTUBE_VIDEO_IDS is set in .env, poll those comma-separated videos.
  2. Otherwise, discover recent videos with YOUTUBE_SEARCH_QUERY and poll them.
  3. For each video, use live chat when it is actively live; otherwise comments.

Usage:
    python producer.py

Optional .env values:
    YOUTUBE_VIDEO_IDS=dQw4w9WgXcQ,abc123...
    YOUTUBE_SEARCH_QUERY=FIFA World Cup 2026 soccer
    YOUTUBE_SEARCH_MAX_RESULTS=5
    YOUTUBE_POLL_INTERVAL_SECS=15
    PRODUCER_DRY_RUN=1       # log real payloads instead of sending to Kafka
    PRODUCER_ONCE=1          # poll once and exit
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from kafka import KafkaProducer
from kafka.errors import KafkaError

load_dotenv()

>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PRODUCER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Kafka Config ──────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS = ["localhost:9092"]
<<<<<<< HEAD
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
=======
TOPIC = "world_cup_firehose"

# ── YouTube Config ────────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "YOUR_API_KEY_HERE")
YOUTUBE_VIDEO_IDS = [
    video_id.strip()
    for video_id in os.getenv("YOUTUBE_VIDEO_IDS", "").split(",")
    if video_id.strip()
]
YOUTUBE_SEARCH_QUERY = os.getenv("YOUTUBE_SEARCH_QUERY", "FIFA World Cup 2026 soccer")
YOUTUBE_SEARCH_MAX_RESULTS = int(os.getenv("YOUTUBE_SEARCH_MAX_RESULTS", "5"))
POLL_INTERVAL_SECS = int(os.getenv("YOUTUBE_POLL_INTERVAL_SECS", "15"))
MAX_RESULTS_PER_CALL = 100
DRY_RUN = os.getenv("PRODUCER_DRY_RUN", "0") == "1"
RUN_ONCE = os.getenv("PRODUCER_ONCE", "0") == "1"


def create_kafka_producer() -> KafkaProducer:
    """Initialize the Kafka producer with retry logic."""
    if DRY_RUN:
        log.info("Dry-run mode enabled — real YouTube payloads will be logged, not sent to Kafka.")
        return None

>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
    retries = 0
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
<<<<<<< HEAD
                # Async batching — accumulate up to 16 KB or 10 ms before sending
                linger_ms=10,
                batch_size=16384,
                # Retries on transient Kafka errors
=======
                linger_ms=10,
                batch_size=16384,
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
                retries=5,
                acks="all",
            )
            log.info("Kafka producer connected to %s", BOOTSTRAP_SERVERS)
            return producer
        except KafkaError as e:
            retries += 1
            wait = min(2 ** retries, 30)
<<<<<<< HEAD
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
=======
            log.warning("Cannot connect to Kafka (attempt %d): %s. Retrying in %ds...", retries, e, wait)
            time.sleep(wait)


def create_youtube_client():
    if "YOUR_API_KEY_HERE" in YOUTUBE_API_KEY:
        log.error("=" * 60)
        log.error("  YouTube API key not configured.")
        log.error("  Add YOUTUBE_API_KEY to .env before running producer.py.")
        log.error("=" * 60)
        sys.exit(1)
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def discover_video_ids(youtube) -> list[str]:
    """Return configured video IDs or discover recent videos for the search query."""
    if YOUTUBE_VIDEO_IDS:
        log.info("Using %d configured YouTube video ID(s) from .env", len(YOUTUBE_VIDEO_IDS))
        return YOUTUBE_VIDEO_IDS

    try:
        resp = youtube.search().list(
            part="id,snippet",
            q=YOUTUBE_SEARCH_QUERY,
            type="video",
            order="date",
            maxResults=YOUTUBE_SEARCH_MAX_RESULTS,
            safeSearch="none",
        ).execute()
    except HttpError as e:
        log.error("YouTube video discovery failed: %s", e)
        return []

    video_ids = []
    for item in resp.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        title = item.get("snippet", {}).get("title", "Untitled")
        if video_id:
            video_ids.append(video_id)
            log.info("Discovered YouTube video: %s — %s", video_id, title[:80])

    return video_ids


def resolve_live_chat_id(youtube, video_id: str) -> str | None:
    """Return the active liveChatId for a video, or None if it is not live."""
    try:
        resp = youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
        items = resp.get("items", [])
        if not items:
            return None
        details = items[0].get("liveStreamingDetails", {})
        return details.get("activeLiveChatId")
    except HttpError as e:
        log.warning("Could not resolve live chat for %s: %s", video_id, e)
        return None


def publish_payload(kafka_producer: KafkaProducer | None, payload: dict):
    if kafka_producer is None:
        log.info("DRY RUN payload: [%s] %s", payload.get("source"), payload.get("text", "")[:120])
        return

    future = kafka_producer.send(TOPIC, value=payload)
    future.add_errback(lambda exc: log.error("Kafka delivery failed: %s", exc))


def poll_live_chat(
    youtube,
    kafka_producer: KafkaProducer,
    video_id: str,
    live_chat_id: str,
    page_token: str | None,
    post_id_start: int,
) -> tuple[str | None, int]:
    """Poll one page of live chat messages. Returns (next_page_token, next_post_id)."""
    post_id = post_id_start
    try:
        resp = youtube.liveChatMessages().list(
            liveChatId=live_chat_id,
            part="snippet,authorDetails",
            pageToken=page_token,
            maxResults=MAX_RESULTS_PER_CALL,
        ).execute()
    except HttpError as e:
        log.warning("Live chat poll failed for %s: %s", video_id, e)
        return page_token, post_id

    published = 0
    for item in resp.get("items", []):
        snippet = item.get("snippet", {})
        text = snippet.get("displayMessage", "").strip()
        if not text:
            continue

        publish_payload(kafka_producer, {
            "id": post_id,
            "text": text[:512],
            "timestamp": int(time.time()),
            "source": "youtube_live_chat",
            "subreddit": "YouTube",
            "reddit_id": item.get("id", "")[:50],
            "score": 0,
            "permalink": f"https://www.youtube.com/watch?v={video_id}",
        })
        post_id += 1
        published += 1

    if published:
        log.info("Published %d YouTube live-chat messages from %s", published, video_id)

    return resp.get("nextPageToken"), post_id


def poll_comments(
    youtube,
    kafka_producer: KafkaProducer,
    video_id: str,
    seen_ids: set,
    post_id_start: int,
) -> int:
    """Poll newest top-level comments for a video. Returns updated post_id counter."""
    post_id = post_id_start
    try:
        resp = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            order="time",
            maxResults=MAX_RESULTS_PER_CALL,
            textFormat="plainText",
        ).execute()
    except HttpError as e:
        log.warning("Comment poll failed for %s: %s", video_id, e)
        return post_id

    published = 0
    for item in resp.get("items", []):
        comment_id = item.get("id", "")
        if not comment_id or comment_id in seen_ids:
            continue
        seen_ids.add(comment_id)

        top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        text = top.get("textDisplay", "").strip()
        if not text:
            continue

        publish_payload(kafka_producer, {
            "id": post_id,
            "text": text[:512],
            "timestamp": int(time.time()),
            "source": "youtube_comment",
            "subreddit": "YouTube",
            "reddit_id": comment_id[:50],
            "score": int(top.get("likeCount", 0)),
            "permalink": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
        })
        post_id += 1
        published += 1

    if published:
        log.info("Published %d YouTube comments from %s", published, video_id)

    return post_id


def run():
    youtube = create_youtube_client()
    video_ids = discover_video_ids(youtube)
    if not video_ids:
        log.error("No YouTube videos available to track. Set YOUTUBE_VIDEO_IDS or adjust YOUTUBE_SEARCH_QUERY.")
        sys.exit(1)

    kafka_producer = create_kafka_producer()
    post_id = 30000
    live_chat_state = {}
    comment_seen = {video_id: set() for video_id in video_ids}

    log.info("═" * 60)
    log.info("  World Cup 2026 YouTube Ingestion Producer — LIVE DATA")
    log.info("  Tracking: %d video(s)", len(video_ids))
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
    log.info("  Topic   : %s", TOPIC)
    log.info("  Servers : %s", BOOTSTRAP_SERVERS)
    log.info("═" * 60)

    try:
        while True:
<<<<<<< HEAD
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
=======
            for video_id in video_ids:
                if video_id not in live_chat_state:
                    chat_id = resolve_live_chat_id(youtube, video_id)
                    live_chat_state[video_id] = {"chat_id": chat_id, "page_token": None}
                    log.info("%s -> %s", video_id, "LIVE CHAT" if chat_id else "COMMENTS")

                state = live_chat_state[video_id]
                if state["chat_id"]:
                    next_token, post_id = poll_live_chat(
                        youtube,
                        kafka_producer,
                        video_id,
                        state["chat_id"],
                        state["page_token"],
                        post_id,
                    )
                    state["page_token"] = next_token
                else:
                    post_id = poll_comments(youtube, kafka_producer, video_id, comment_seen[video_id], post_id)

            if kafka_producer is not None:
                kafka_producer.flush(timeout=5)
            if RUN_ONCE:
                log.info("One-shot mode complete.")
                return
            time.sleep(POLL_INTERVAL_SECS)

    except KeyboardInterrupt:
        log.info("Shutdown signal received — flushing remaining messages...")
        if kafka_producer is not None:
            kafka_producer.flush(timeout=10)
            kafka_producer.close()
        log.info("Producer halted cleanly.")
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
        sys.exit(0)


if __name__ == "__main__":
    run()
