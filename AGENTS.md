# AGENTS for the FIFA World Cup 2026 Sentiment Tracker

Use this file as the shared playbook for improving the project. Each major file has a clear responsibility and a preferred direction for upgrades.

## Global rules
- Prefer small, targeted improvements over large rewrites.
- Keep the project modular: producers, consumer, dashboard, and infrastructure should stay loosely coupled.
- Preserve the existing Kafka → consumer → database → dashboard flow unless a change clearly improves it.
- Do not hardcode secrets. Read credentials from environment variables or a local .env file.
- Favor readable, well-documented Python over clever one-liners.
- Add logging and error handling where data flow could fail.
- Keep compatibility with the current Docker and Python setup.

## File-specific guidance

### producer.py
- Improve the simulation logic so it better resembles real match-day traffic spikes.
- Keep the producer simple and deterministic enough for testing.
- Preserve the current Kafka topic contract.
- Add optional configuration for rate, burst frequency, and message variety.

### producer_reddit.py
- Improve filtering quality and resilience for Reddit API failures.
- Keep credentials out of source code.
- Add graceful handling for rate limits, deleted comments, and empty content.
- Preserve the payload schema expected by the consumer.

### producer_bluesky.py
- Improve filtering logic to reduce noise and false positives.
- Keep translation behavior optional and robust.
- Handle WebSocket reconnects and malformed events more cleanly.
- Preserve the same normalized payload shape for downstream processing.

### producer_youtube.py
- Improve polling efficiency and retry handling.
- Keep live chat and comment ingestion separate and well-documented.
- Avoid hitting API quota limits unnecessarily.
- Preserve compatibility with the Kafka pipeline.

### producer_twitter.py
- Improve stream rule management and reconnection behavior.
- Keep authentication externalized and safe.
- Handle rate limits and stream interruptions gracefully.
- Preserve message structure for the consumer.

### consumer.py
- Improve robustness around parsing, batching, model inference, and database writes.
- Keep Dead Letter Queue handling intact for bad messages.
- Prefer explicit, testable functions over tightly coupled logic.
- Improve team extraction quality without breaking existing behavior.
- Keep logging useful for monitoring and debugging.

### dashboard.py
- Improve performance by keeping queries efficient and avoiding unnecessary refreshes.
- Prefer clear visual structure and responsive layout.
- Keep the UI readable and polished for demo use.
- Make data transformations explicit and easy to maintain.

### docker-compose.yml
- Keep infrastructure setup reproducible and simple.
- Preserve the Kafka, Zookeeper, and TimescaleDB runtime relationships.
- Avoid breaking local startup for first-time users.

### init.sql
- Keep the schema stable and compatible with the consumer.
- Improve indexes and views only when they clearly help performance.
- Preserve the hypertable and continuous aggregate design.

## Suggested improvement themes
- Better configuration management with environment variables.
- Stronger observability with structured logs and counters.
- Cleaner code organization using helper functions and small classes where useful.
- More defensive handling of API and database failures.
- Improved filtering quality for social media relevance.

## Quality bar for changes
Before finishing a change, confirm that:
- the relevant script still runs without syntax errors
- the change does not break the producer → Kafka → consumer → database flow
- the behavior is documented clearly enough for a new contributor
