"""
producer_youtube.py — FIFA World Cup 2026 YouTube Live Chat & Comments Producer

Publishes YouTube live-chat messages (during match broadcasts) and/or video
comments (for highlight reels, post-match recaps, etc.) to the same
`world_cup_firehose` Kafka topic consumed by consumer.py.

Why YouTube: it's one of the few "big" platforms with a genuinely free,
official, ToS-compliant API. No paid tier, no scraping.

Setup (one-time):
    1. Go to https://console.cloud.google.com/apis/credentials
    2. Create a project (or reuse one), enable "YouTube Data API v3"
    3. Create an API key
    4. Set it as YOUTUBE_API_KEY below, as an env var, or in a .env file

Quota note:
    The free daily quota is 10,000 units. live_chat polling costs ~1-5 units
    per call depending on part size; comments.list costs 1 unit per page.
    Polling every POLL_INTERVAL_SECS with a couple of chats/videos tracked
    comfortably stays inside the free quota for a match window.

Two modes (auto-selected per target):
    LIVE CHAT — for an active livestream video ID, polls liveChatMessages
    COMMENTS  — for a regular (non-live) video ID, polls commentThreads

Usage:
    python producer_youtube.py
"""

from __future__ import annotations

import json
import time
import logging
import sys
import os

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from kafka import KafkaProducer
from kafka.errors import KafkaError

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [YOUTUBE] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "YOUR_API_KEY_HERE")
BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC = "world_cup_firehose"

# Fill in with video IDs you want to track. Mix of:
#  - Live broadcast video IDs (official FIFA / broadcaster match streams)
#  - Regular video IDs (highlight reels, recap videos) for comment polling
# The 11-char ID is the part after "v=" in a YouTube URL.
TRACKED_VIDEO_IDS: list[str] = [
    # "dQw4w9WgXcQ",  # <- replace with real match broadcast / highlight IDs
]

POLL_INTERVAL_SECS = 8       # how often to re-poll each tracked video
MAX_RESULTS_PER_CALL = 200   # live chat: up to 2000; comments: up to 100


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


def create_youtube_client():
    if "YOUR_API_KEY_HERE" in YOUTUBE_API_KEY:
        log.error("=" * 60)
        log.error("  YouTube API key not configured!")
        log.error("  Set YOUTUBE_API_KEY as an env var or in a .env file.")
        log.error("  See setup instructions at the top of this file.")
        log.error("=" * 60)
        sys.exit(1)
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def resolve_live_chat_id(youtube, video_id: str) -> str | None:
    """Return the active liveChatId for a video, or None if it's not live."""
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


def poll_live_chat(youtube, kafka_producer, video_id: str, live_chat_id: str, page_token: str | None, post_id_start: int) -> tuple[str | None, int, int]:
    """Poll one page of live chat messages. Returns (next_page_token, next_delay_ms, new_post_id_counter)."""
    published = 0
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
        return page_token, 8000, post_id

    for item in resp.get("items", []):
        snippet = item.get("snippet", {})
        text = snippet.get("displayMessage", "").strip()
        if not text:
            continue

        payload = {
            "id": post_id,
            "text": text[:512],
            "timestamp": int(time.time()),
            "source": "youtube_live_chat",
            "subreddit": "YouTube",  # reuse field for UI source labeling
            "reddit_id": item.get("id", "")[:50],
            "score": 0,
            "permalink": f"https://www.youtube.com/watch?v={video_id}",
        }
        future = kafka_producer.send(TOPIC, value=payload)
        future.add_errback(lambda exc: log.error("Kafka delivery failed: %s", exc))
        published += 1
        post_id += 1

    if published:
        log.info("📨 [%s] +%d live chat messages", video_id, published)

    next_page_token = resp.get("nextPageToken")
    polling_interval_ms = resp.get("pollingIntervalMillis", 8000)
    return next_page_token, polling_interval_ms, post_id


def poll_comments(youtube, kafka_producer, video_id: str, seen_ids: set, post_id_start: int) -> int:
    """Poll top-level comment threads for a non-live video. Returns updated post_id counter."""
    post_id = post_id_start
    try:
        resp = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            order="time",
            maxResults=100,
            textFormat="plainText",
        ).execute()
    except HttpError as e:
        log.warning("Comment poll failed for %s: %s", video_id, e)
        return post_id

    for item in resp.get("items", []):
        comment_id = item.get("id", "")
        if comment_id in seen_ids:
            continue
        seen_ids.add(comment_id)

        top = item["snippet"]["topLevelComment"]["snippet"]
        text = top.get("textDisplay", "").strip()
        if not text:
            continue

        payload = {
            "id": post_id,
            "text": text[:512],
            "timestamp": int(time.time()),
            "source": "youtube_comment",
            "subreddit": "YouTube",
            "reddit_id": comment_id[:50],
            "score": int(top.get("likeCount", 0)),
            "permalink": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
        }
        future = kafka_producer.send(TOPIC, value=payload)
        future.add_errback(lambda exc: log.error("Kafka delivery failed: %s", exc))
        post_id += 1

    return post_id


def run():
    if not TRACKED_VIDEO_IDS:
        log.error("TRACKED_VIDEO_IDS is empty — add match broadcast / highlight video IDs before running.")
        sys.exit(1)

    kafka_producer = create_kafka_producer()
    youtube = create_youtube_client()

    post_id = 30000  # distinct ID range for YouTube sources
    live_chat_state: dict[str, dict] = {}   # video_id -> {"chat_id":..., "page_token":...}
    comment_seen: dict[str, set] = {vid: set() for vid in TRACKED_VIDEO_IDS}

    log.info("═" * 60)
    log.info("  FIFA World Cup 2026 YouTube Producer — LIVE")
    log.info("  Tracking %d video(s)", len(TRACKED_VIDEO_IDS))
    log.info("  Kafka Topic: %s", TOPIC)
    log.info("═" * 60)

    try:
        while True:
            for video_id in TRACKED_VIDEO_IDS:
                # Try live chat first; fall back to comments if not live
                if video_id not in live_chat_state:
                    chat_id = resolve_live_chat_id(youtube, video_id)
                    live_chat_state[video_id] = {"chat_id": chat_id, "page_token": None}
                    log.info("%s → %s", video_id, "LIVE CHAT" if chat_id else "COMMENTS (not live)")

                state = live_chat_state[video_id]
                if state["chat_id"]:
                    next_token, delay_ms, post_id = poll_live_chat(
                        youtube, kafka_producer, video_id, state["chat_id"], state["page_token"], post_id
                    )
                    state["page_token"] = next_token
                else:
                    post_id = poll_comments(youtube, kafka_producer, video_id, comment_seen[video_id], post_id)

            time.sleep(POLL_INTERVAL_SECS)

    except KeyboardInterrupt:
        log.info("Shutdown signal — flushing Kafka producer…")
        kafka_producer.flush(timeout=10)
        kafka_producer.close()
        log.info("YouTube producer stopped.")
        sys.exit(0)


if __name__ == "__main__":
    run()
