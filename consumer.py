<<<<<<< HEAD
=======
from __future__ import annotations

>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
"""
consumer.py — FIFA World Cup 2026 ML Inference & Persistence Engine

Reads raw posts from the `world_cup_firehose` Kafka topic in micro-batches,
identifies the target national team using a rich keyword/nickname/player map,
runs batch sentiment inference via DistilBERT (SST-2), and persists structured
records to TimescaleDB.

Dead Letter Queue (DLQ):
  Any payload that fails parsing, entity extraction, or model inference is
  caught, tagged, and routed to the `world_cup_dlq` Kafka topic so the main
  loop is never interrupted.

Usage:
    python consumer.py
"""

import json
<<<<<<< HEAD
=======
import os
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
import time
import logging
import sys
from datetime import datetime, timezone

<<<<<<< HEAD
import psycopg
from psycopg.rows import dict_row
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from transformers import pipeline
=======
from dotenv import load_dotenv

load_dotenv()

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - only exercised when deps are missing
    psycopg = None
    dict_row = None

try:
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import KafkaError
except ImportError:  # pragma: no cover - only exercised when deps are missing
    KafkaConsumer = None
    KafkaProducer = None
    KafkaError = Exception

try:
    from transformers import pipeline
except ImportError:  # pragma: no cover - only exercised when deps are missing
    pipeline = None
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CONSUMER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
<<<<<<< HEAD
BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC_MAIN        = "world_cup_firehose"
TOPIC_DLQ         = "world_cup_dlq"
GROUP_ID          = "wc-sentiment-group"

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "world_cup_sentiment",
    "user":     "postgres",
    "password": "password",
=======
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
TOPIC_MAIN        = os.getenv("KAFKA_TOPIC_MAIN", "world_cup_firehose")
TOPIC_DLQ         = os.getenv("KAFKA_TOPIC_DLQ", "world_cup_dlq")
GROUP_ID          = os.getenv("KAFKA_GROUP_ID", "wc-sentiment-group")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME", "world_cup_sentiment"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
}

BATCH_SIZE    = 16    # target micro-batch size (posts)
MAX_WAIT_SECS = 1.5   # max seconds to wait before flushing a partial batch
MAX_TEXT_LEN  = 512   # DistilBERT token limit guard (characters)

# ── Entity Keyword Mapping ────────────────────────────────────────────────────
# Maps rich contextual signals (squad nicknames, player names, hashtags,
# coach names) → canonical nation ID used in the database.
TEAM_KEYWORDS: dict[str, list[str]] = {
    "USA": [
        "usa", "usmnt", "united states", "team usa",
        "pulisic", "balogun", "folarin", "weah", "aaronson",
        "berhalter", "turner",
    ],
    "Mexico": [
        "mexico", "méxico", "el tri", "tri", "aztecas",
        "lozano", "jimenez", "raul jimenez", "gimenez", "santi gimenez",
        "santiago gimenez", "edson", "guardado", "ochoa", "el piojo",
    ],
    "Canada": [
        "canada", "canmnt", "les rouges",
        "davies", "alphonso", "david", "jonathan david",
        "buchanan", "laryea", "herdman",
    ],
    "Argentina": [
        "argentina", "albiceleste", "scaloneta",
        "messi", "lionel messi", "di maria", "de paul", "martinez",
        "lautaro", "scaloni",
    ],
    "Brazil": [
        "brazil", "brasil", "seleção", "selecao", "canarinha",
        "vinicius", "vinicius jr", "rodrygo", "raphinha", "endrick",
        "neymar", "ancelotti",
    ],
    "France": [
        "france", "les bleus", "equipe de france",
        "mbappe", "mbappé", "dembele", "dembélé", "griezmann",
        "giroud", "rabiot", "deschamps",
    ],
    "Germany": [
        "germany", "deutschland", "die mannschaft",
        "muller", "müller", "gnabry", "musiala", "havertz",
        "kroos", "neuer", "nagelsmann",
    ],
    "England": [
<<<<<<< HEAD
        "england", "three lions", "gareth southgate", "southgate",
        "bellingham", "saka", "kane", "harry kane",
        "foden", "trippier", "rashford",
=======
        "england", "three lions", "tuchel", "thomas tuchel",
        "bellingham", "saka", "kane", "harry kane",
        "foden", "konsa", "rashford",
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
    ],
    "Spain": [
        "spain", "españa", "la roja", "la furia roja",
        "pedri", "gavi", "morata", "yamal", "lamine",
        "rodri", "de bruyne", "olmo", "luis de la fuente",
    ],
    "Portugal": [
        "portugal", "seleção das quinas",
        "ronaldo", "cristiano", "felix", "joao felix",
        "bruno fernandes", "bernardo silva", "leao",
    ],
}


def extract_target_team(text: str) -> str:
    """Return the first matched team name, or 'Neutral/General'."""
    lowered = text.lower()
    for team, keywords in TEAM_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return team
    return "Neutral/General"


<<<<<<< HEAD
# ── Model Initialization ──────────────────────────────────────────────────────
def load_model():
    """Load DistilBERT sentiment pipeline. Auto-detects CUDA if available."""
=======
def normalize_text(text: str, max_len: int = MAX_TEXT_LEN) -> str:
    """Trim noisy translation suffixes, normalize whitespace, and enforce a safe length."""
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""

    if " [Original: " in cleaned:
        cleaned = cleaned.split(" [Original: ", 1)[0]

    cleaned = " ".join(cleaned.split())
    return cleaned[:max_len]


# ── Model Initialization ──────────────────────────────────────────────────────
def load_model():
    """Load DistilBERT sentiment pipeline. Auto-detects CUDA if available."""
    if pipeline is None:
        raise RuntimeError("transformers is not installed. Install requirements first.")

>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
    try:
        import torch
        device = 0 if torch.cuda.is_available() else -1
        device_label = f"GPU (CUDA device {device})" if device == 0 else "CPU"
    except ImportError:
        device = -1
        device_label = "CPU"

    log.info("Loading DistilBERT on %s…", device_label)
    model = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        device=device,
        truncation=True,
        max_length=512,
    )
    log.info("✅ Sentiment pipeline ready (%s)", device_label)
    return model


# ── Database ──────────────────────────────────────────────────────────────────
def get_db_connection():
    """Open a persistent PostgreSQL connection with retry logic."""
<<<<<<< HEAD
=======
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Install requirements first.")

>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
    connstr = (
        f"host={DB_CONFIG['host']} port={DB_CONFIG['port']} "
        f"dbname={DB_CONFIG['dbname']} user={DB_CONFIG['user']} "
        f"password={DB_CONFIG['password']}"
    )
    retries = 0
    while True:
        try:
            conn = psycopg.connect(connstr)
            conn.autocommit = False
            log.info("✅ TimescaleDB connected at %s:%s", DB_CONFIG["host"], DB_CONFIG["port"])
            return conn
        except psycopg.OperationalError as e:
            retries += 1
            wait = min(2 ** retries, 30)
            log.warning("DB connection failed (attempt %d): %s. Retrying in %ds…", retries, e, wait)
            time.sleep(wait)


INSERT_SQL = """
    INSERT INTO match_sentiment
        (post_time, post_id, target_team, sentiment_label, confidence_score, raw_text)
    VALUES (%s, %s, %s, %s, %s, %s)
"""


def persist_batch(conn, records: list[dict]):
    """Bulk-insert a batch of analyzed records into TimescaleDB."""
    rows = [
        (
            datetime.fromtimestamp(r["timestamp"], tz=timezone.utc),
            r["id"],
            r["team"],
            r["sentiment"],
            r["confidence"],
            r["text"][:1000],  # guard against oversized text in DB
        )
        for r in records
    ]
    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, rows)
    conn.commit()


# ── Kafka Helpers ─────────────────────────────────────────────────────────────
<<<<<<< HEAD
def create_consumer() -> KafkaConsumer:
=======
def create_consumer():
    if KafkaConsumer is None:
        raise RuntimeError("kafka-python is not installed. Install requirements first.")

>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
    retries = 0
    while True:
        try:
            c = KafkaConsumer(
                TOPIC_MAIN,
                bootstrap_servers=BOOTSTRAP_SERVERS,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id=GROUP_ID,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                fetch_max_bytes=1_048_576,   # 1 MB per fetch
                max_poll_records=64,
            )
            log.info("Kafka consumer subscribed to topic '%s'", TOPIC_MAIN)
            return c
        except KafkaError as e:
            retries += 1
            wait = min(2 ** retries, 30)
            log.warning("Kafka consumer init failed (attempt %d): %s. Retrying in %ds…", retries, e, wait)
            time.sleep(wait)


<<<<<<< HEAD
def create_dlq_producer() -> KafkaProducer:
=======
def create_dlq_producer():
    if KafkaProducer is None:
        raise RuntimeError("kafka-python is not installed. Install requirements first.")

>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=3,
    )


<<<<<<< HEAD
def send_to_dlq(dlq_producer: KafkaProducer, raw_value, error: str):
=======
def send_to_dlq(dlq_producer, raw_value, error: str):
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)
    """Route a faulty payload to the Dead Letter Queue topic."""
    try:
        dlq_payload = {
            "error":     error,
            "raw":       str(raw_value)[:2000],
            "dlq_time":  int(time.time()),
        }
        dlq_producer.send(TOPIC_DLQ, value=dlq_payload)
        log.warning("⚠️  DLQ — routed faulty message: %s", error[:80])
    except Exception as dlq_exc:
        log.error("Failed to send message to DLQ: %s", dlq_exc)


# ── Main Processing Loop ──────────────────────────────────────────────────────
def run():
    sentiment_pipeline = load_model()
    conn               = get_db_connection()
    consumer           = create_consumer()
    dlq_producer       = create_dlq_producer()

    buffer: list[dict] = []
    last_flush         = time.time()
    total_processed    = 0
    total_errors       = 0

    log.info("═" * 60)
    log.info("  World Cup 2026 Inference Engine — OPERATIONAL")
    log.info("  Batch Size : %d posts", BATCH_SIZE)
    log.info("  Max Wait   : %.1f seconds", MAX_WAIT_SECS)
    log.info("  DB Target  : %s/%s", DB_CONFIG["host"], DB_CONFIG["dbname"])
    log.info("═" * 60)

    try:
        while True:
            # ── Poll Kafka ────────────────────────────────────────────────────
            msg_pack = consumer.poll(timeout_ms=100)

            for _tp, messages in msg_pack.items():
                for message in messages:
                    raw_value = message.value

                    # ── Stage 1: Parse & validate ─────────────────────────────
                    try:
<<<<<<< HEAD
                        text = str(raw_value.get("text", "")).strip()

                        if not text:
                            raise ValueError("Empty text field")
                        if len(text) > MAX_TEXT_LEN:
                            # Truncate rather than discard — still valuable signal
                            text = text[:MAX_TEXT_LEN]
=======
                        text = normalize_text(raw_value.get("text", ""))

                        if not text:
                            raise ValueError("Empty text field")
>>>>>>> aad0f38 (Improve consumer robustness and add agent workflow)

                        # Encode/decode round-trip to catch bad character sequences
                        text.encode("utf-8").decode("utf-8")

                        team = extract_target_team(text)

                        buffer.append({
                            "id":        raw_value.get("id", -1),
                            "text":      text,
                            "timestamp": raw_value.get("timestamp", int(time.time())),
                            "team":      team,
                        })

                    except Exception as parse_err:
                        total_errors += 1
                        send_to_dlq(dlq_producer, raw_value, f"PARSE_ERROR: {parse_err}")
                        continue

            # ── Stage 2: Flush batch when ready ──────────────────────────────
            time_delta = time.time() - last_flush
            should_flush = (
                len(buffer) >= BATCH_SIZE
                or (len(buffer) > 0 and time_delta >= MAX_WAIT_SECS)
            )

            if not should_flush:
                continue

            batch      = buffer[:BATCH_SIZE]
            buffer     = buffer[BATCH_SIZE:]
            last_flush = time.time()

            # ── Stage 3: ML Inference ─────────────────────────────────────────
            try:
                # Split original text if present so that DistilBERT only analyzes the English translation
                texts       = [item["text"].split(" [Original: ")[0] for item in batch]
                predictions = sentiment_pipeline(texts)

                enriched = []
                for item, pred in zip(batch, predictions):
                    enriched.append({
                        **item,
                        "sentiment":  pred["label"],
                        "confidence": round(pred["score"], 4),
                    })

            except Exception as model_err:
                total_errors += len(batch)
                for item in batch:
                    send_to_dlq(dlq_producer, item, f"INFERENCE_ERROR: {model_err}")
                continue

            # ── Stage 4: Persist to TimescaleDB ──────────────────────────────
            try:
                persist_batch(conn, enriched)
            except psycopg.Error as db_err:
                log.error("DB write failed — attempting reconnect: %s", db_err)
                try:
                    conn.rollback()
                    conn = get_db_connection()
                    persist_batch(conn, enriched)
                except Exception as retry_err:
                    total_errors += len(enriched)
                    for item in enriched:
                        send_to_dlq(dlq_producer, item, f"DB_ERROR: {retry_err}")
                    continue

            # ── Stage 5: Log throughput stats ─────────────────────────────────
            total_processed += len(enriched)
            for rec in enriched:
                emoji = "✅" if rec["sentiment"] == "POSITIVE" else "❌"
                log.debug(
                    "%s [%s] %s (%.2f%%)",
                    emoji, rec["team"], rec["text"][:60], rec["confidence"] * 100,
                )

            log.info(
                "📊 Batch stored: %d posts | Total: %d | DLQ errors: %d",
                len(enriched), total_processed, total_errors,
            )

    except KeyboardInterrupt:
        log.info("Shutdown signal received — flushing DLQ producer…")
        dlq_producer.flush(timeout=5)
        dlq_producer.close()
        consumer.close()
        conn.close()
        log.info(
            "Consumer offline. Records processed: %d | DLQ errors: %d",
            total_processed, total_errors,
        )
        sys.exit(0)


if __name__ == "__main__":
    run()
