# Copilot instructions for this repository

This repository contains a real-time social sentiment pipeline for FIFA World Cup 2026. When editing files here, follow these preferences:

- Keep the architecture intact: Kafka producers feed the consumer, which writes to TimescaleDB and powers the Streamlit dashboard.
- Prefer robust, production-minded Python over quick hacks.
- Do not add hardcoded secrets or credentials.
- Use environment variables for API keys and database config.
- Preserve existing payload shapes so the producer and consumer stay compatible.
- Make changes small and clearly scoped.
- Keep comments and docstrings useful, especially around streaming, NLP, and database logic.

## Suggested per-file focus
- producer*.py: improve ingestion reliability and filtering.
- consumer.py: improve NLP handling, batch processing, and error recovery.
- dashboard.py: improve clarity, performance, and visual polish.
- docker-compose.yml and init.sql: keep local setup reproducible.

## Verification expectations
- If you change Python code, check for syntax issues before finishing.
- If you change infrastructure or database files, keep them compatible with the existing compose setup.
