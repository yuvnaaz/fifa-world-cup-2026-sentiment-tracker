# Suggested agent tasks

Use these as implementation prompts for separate agents or contributors.

## Agent 1 — Ingestion reliability
Focus on the producer scripts.
- Improve filtering and normalization.
- Make failures more graceful.
- Keep message format compatible with the consumer.

## Agent 2 — Consumer robustness
Focus on consumer.py.
- Improve batching and error handling.
- Make team extraction smarter and more reliable.
- Preserve DLQ behavior and logging.

## Agent 3 — Dashboard polish
Focus on dashboard.py.
- Improve chart performance and readability.
- Make the UI more polished for demos.
- Keep database queries efficient.

## Agent 4 — Infrastructure hardening
Focus on docker-compose.yml and init.sql.
- Keep startup simple and repeatable.
- Improve resilience and observability.
- Make local onboarding smoother.
