-- ============================================================
-- FIFA World Cup 2026 Sentiment Tracker — TimescaleDB Schema
-- Automatically executed on first container startup.
-- ============================================================

-- Core time-series table for storing per-post sentiment records.
CREATE TABLE IF NOT EXISTS match_sentiment (
    post_time        TIMESTAMPTZ   NOT NULL,
    post_id          BIGINT        NOT NULL,
    target_team      VARCHAR(50)   NOT NULL,
    sentiment_label  VARCHAR(10)   NOT NULL,  -- 'POSITIVE' | 'NEGATIVE'
    confidence_score NUMERIC(5,4)  NOT NULL,
    raw_text         TEXT          NOT NULL
);

-- Convert to a TimescaleDB hypertable partitioned by time.
-- chunk_time_interval = 1 hour keeps chunk sizes manageable during peak traffic.
SELECT create_hypertable(
    'match_sentiment',
    'post_time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Composite index for the most common query pattern:
-- "give me all rows for team X, ordered newest-first"
CREATE INDEX IF NOT EXISTS idx_team_time
    ON match_sentiment (target_team, post_time DESC);

-- Index for fast aggregate scans across all teams in a time window
CREATE INDEX IF NOT EXISTS idx_post_time_brin
    ON match_sentiment USING BRIN (post_time);

-- ============================================================
-- Pre-built continuous aggregate view for the dashboard.
-- Returns per-minute, per-team sentiment roll-up without
-- scanning millions of raw rows on every UI refresh.
-- ============================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS sentiment_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', post_time)  AS minute_window,
    target_team,
    COUNT(*)                             AS total_posts,
    COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE') AS positive_count,
    COUNT(*) FILTER (WHERE sentiment_label = 'NEGATIVE') AS negative_count,
    ROUND(
        (COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE')::NUMERIC / COUNT(*)) * 100,
        2
    )                                    AS fan_positivity_pct
FROM match_sentiment
GROUP BY minute_window, target_team
WITH NO DATA;

-- Refresh policy: keep the view up-to-date as new rows arrive.
SELECT add_continuous_aggregate_policy(
    'sentiment_1min',
    start_offset => INTERVAL '2 hours',
    end_offset   => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);
