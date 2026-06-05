🏆 FIFA World Cup 2026 Fan Sentiment Tracker
A real-time sentiment intelligence pipeline and interactive analytics dashboard built for the FIFA World Cup 2026.

Designed to handle massive social media traffic spikes during key match moments (goals, red cards, penalties), the system decouples fast data ingestion from heavy NLP processing. It uses Apache Kafka as a buffer, DistilBERT for sentiment classification, TimescaleDB for time-series storage, and a modern Streamlit dashboard for visualization.

🚀 Key Features
⚡ Real-Time Ingestion: Connects directly to the Bluesky Jetstream firehose for live social data.

🌍 Auto-Translation: Detects language automatically and translates foreign posts to English for accurate sentiment analysis.

🛡️ Smart Noise Filter: Ensures data relevance by bypassing general internet noise and validating soccer-specific context.

🚦 Kafka Shock Absorber: Buffers the incoming stream to prevent database bottlenecks during viral match moments.

🧠 ML Inference: Uses a fine-tuned DistilBERT model to classify posts as Positive or Negative in micro-batches.

📊 Premium Analytics Dashboard: A sleek, dark-themed visual command center featuring:

High-impact KPI row (Velocity, Confidence, Volume).

Spline-smoothed sentiment trend charts.

Interactive world map for country-specific sentiment drill-downs.

Live feed ticker and top trending topics.

🛠️ Technology Stack
Frontend: Python, Streamlit, Plotly, HTML/CSS

Message Broker: Apache Kafka, Apache Zookeeper

Database: TimescaleDB (PostgreSQL 15 extension)

ML Engine: Hugging Face Transformers, PyTorch (DistilBERT)

Infrastructure: Docker, Docker Compose
