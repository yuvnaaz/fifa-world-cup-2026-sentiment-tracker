"""
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

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PRODUCER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Kafka Config ──────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS = ["localhost:9092"]
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


def create_kafka_producer() -> KafkaProducer | None:
    """Initialize the Kafka producer with retry logic."""
    if DRY_RUN:
        log.info("Dry-run mode enabled — real YouTube payloads will be logged, not sent to Kafka.")
        return None

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
            log.info("Kafka producer connected to %s", BOOTSTRAP_SERVERS)
            return producer
        except KafkaError as e:
            retries += 1
            wait = min(2 ** retries, 30)
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
    kafka_producer: KafkaProducer | None,
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
    kafka_producer: KafkaProducer | None,
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
    log.info("  Topic   : %s", TOPIC)
    log.info("  Servers : %s", BOOTSTRAP_SERVERS)
    log.info("═" * 60)

    try:
        while True:
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
        sys.exit(0)


if __name__ == "__main__":
    run()
