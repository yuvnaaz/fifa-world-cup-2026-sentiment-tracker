🏆 FIFA World Cup 2026 Fan Sentiment Tracker
A real-time sentiment intelligence pipeline and interactive analytics dashboard built for the FIFA World Cup 2026.

Designed to handle massive social media traffic spikes during key match moments (goals, red cards, penalties), the system decouples fast data ingestion from heavy NLP processing. It uses Apache Kafka as a buffer, DistilBERT for sentiment classification, TimescaleDB for time-series storage, and a modern Streamlit dashboard for visualization.

🚀 Key Features
⚡ Real-Time Ingestion: Pulls from Reddit, Bluesky Jetstream, YouTube (live chat + comments), and X/Twitter (filtered stream, paid tier) into one unified firehose.

🌍 Auto-Translation: Detects language automatically and translates foreign posts to English for accurate sentiment analysis.

🛡️ Smart Noise Filter: Ensures data relevance by bypassing general internet noise and validating soccer-specific context.

🚦 Kafka Shock Absorber: Buffers the incoming stream to prevent database bottlenecks during viral match moments.

🧠 ML Inference: Uses a fine-tuned DistilBERT model to classify posts as Positive or Negative in micro-batches.

📈 Dynamic Trending Topics: Discovers what's actually being talked about in real time (hashtags + n-gram frequency analysis) rather than a fixed keyword list — known players/teams get a relevance boost but don't crowd out new spikes (a coach, a controversial call, a breakout hashtag).

📊 Premium Analytics Dashboard: A sleek, dark-themed visual command center featuring:

High-impact KPI row (Velocity, Confidence, Volume).

Spline-smoothed sentiment trend charts.

Interactive world map for country-specific sentiment drill-downs.

Live feed ticker and top trending topics.

📡 Data Sources
| Source | Method | Cost | Notes |
|---|---|---|---|
| Reddit | `producer_reddit.py` — PRAW comment stream | Free | Needs a Reddit script app (client id/secret) |
| Bluesky | `producer_bluesky.py` — Jetstream WebSocket firehose | Free | No auth required at all |
| YouTube | `producer_youtube.py` — Data API v3 live chat / comments | Free (10k unit/day quota) | Needs an API key; you supply video IDs to track |
| X (Twitter) | `producer_twitter.py` — v2 filtered stream | Paid (Basic tier+, ~$200/mo) | Free tier no longer includes filtered stream access |
| TikTok | *(not implemented)* | — | No free/ToS-compliant real-time API exists; official Research API is application-only and not a firehose. Not included to avoid scraping. |

Run any subset of the producers simultaneously — they all publish to the same `world_cup_firehose` Kafka topic.

🛠️ Technology Stack
Frontend: Python, Streamlit, Plotly, HTML/CSS

Message Broker: Apache Kafka, Apache Zookeeper

Database: TimescaleDB (PostgreSQL 15 extension)

ML Engine: Hugging Face Transformers, PyTorch (DistilBERT)

Infrastructure: Docker, Docker Compose
