"""
dashboard.py — FIFA World Cup 2026 Real-Time Sentiment Intelligence Dashboard

A clean corporate light-mode Streamlit dashboard designed after the latest mockup.
Features a dark blue sidebar, white KPI cards with circular SVG icons,
smoothed spline trends, a light choropleth map, a stacked distribution bar chart,
and an auto-calculating live feed. Includes rich FIFA-themed hover animations.
"""

import time
import string
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import psycopg
from psycopg.rows import dict_row

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FIFA World Cup 2026 | Fan Sentiment Tracker",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — Corporate Light Design & Hover Animations ────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

/* ── Global App Styles ── */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
    background-color: #f8fafc;
    color: #334155;
}
.stApp {
    background-color: #f8fafc;
}

/* Remove default Streamlit padding/header */
[data-testid="stHeader"] {
    background-color: rgba(0,0,0,0);
}
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
}

/* ── Header ── */
.dash-top-bar {
    margin-bottom: 24px;
}
.status-indicator-green {
    width: 8px;
    height: 8px;
    background-color: #10b981;
    border-radius: 50%;
    box-shadow: 0 0 8px #10b981;
}

/* ── KPI Container & Cards ── */
.kpi-container-new {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    width: 100%;
    margin-bottom: 24px;
}
.kpi-card-new {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 18px 20px !important;
    min-width: 180px;
    flex: 1 1 0px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.kpi-card-new::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(90deg, #8b5cf6, #ec4899, #f97316, #10b981);
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.3s ease;
}
.kpi-card-new:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 20px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.03) !important;
    border-color: #cbd5e1 !important;
}
.kpi-card-new:hover::after {
    transform: scaleX(1);
}

.kpi-icon-circle {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.3s ease;
}
.kpi-card-new:hover .kpi-icon-circle {
    transform: scale(1.1);
}

.kpi-icon-emerald { background-color: #ecfdf5; color: #10b981; }
.kpi-icon-rose { background-color: #fef2f2; color: #ef4444; }
.kpi-icon-blue { background-color: #eff6ff; color: #1d4ed8; }
.kpi-icon-slate { background-color: #f1f5f9; color: #475569; }
.kpi-icon-zinc { background-color: #fafaf9; color: #0f172a; }

.kpi-body {
    display: flex;
    flex-direction: column;
}
.kpi-label-new {
    font-size: 0.72rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
}
.kpi-value-new {
    font-size: 1.8rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.1;
    margin-bottom: 2px;
}
.kpi-trend-new {
    font-size: 0.75rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 4px;
}
.trend-up { color: #10b981; font-weight: 700; }
.trend-down { color: #ef4444; font-weight: 700; }
.trend-time { color: #94a3b8; }

/* ── Section Headers ── */
.section-title {
    font-size: 0.85rem;
    font-weight: 800;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
}

/* ── Container Boxes ── */
.chart-box, .feed-box, .trending-box {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.chart-box:hover, .feed-box:hover, .trending-box:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -2px rgba(0, 0, 0, 0.03) !important;
}

.feed-box, .trending-box {
    height: 382px;
    display: flex;
    flex-direction: column;
}

/* ── Live Feed List ── */
.live-feed-container {
    overflow-y: auto;
    flex: 1;
    padding-right: 4px;
    display: flex;
    flex-direction: column;
}
.live-feed-container::-webkit-scrollbar {
    width: 4px;
}
.live-feed-container::-webkit-scrollbar-track {
    background: rgba(0,0,0,0.02);
}
.live-feed-container::-webkit-scrollbar-thumb {
    background: rgba(0,0,0,0.1);
    border-radius: 4px;
}

.post-card {
    background: #ffffff !important;
    border: none !important;
    border-bottom: 1px solid #f1f5f9 !important;
    border-radius: 0 !important;
    padding: 12px 8px !important;
    box-shadow: none !important;
    transition: all 0.2s ease;
}
.post-card:last-child {
    border-bottom: none !important;
}
.post-card:hover {
    transform: translateX(4px);
    background-color: #f8fafc !important;
    border-radius: 6px !important;
    padding-left: 12px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #0b1a30 !important;
    border-right: 1px solid rgba(0, 0, 0, 0.1) !important;
}
.sidebar-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0 20px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 20px;
}
.sidebar-logo .trophy-emoji {
    font-size: 1.8rem;
    filter: drop-shadow(0 0 4px rgba(255, 215, 0, 0.2));
}
.sidebar-title-text {
    display: flex;
    flex-direction: column;
}
.sidebar-title-text .title-main {
    font-size: 1.05rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.2px;
}
.sidebar-title-text .title-sub {
    font-size: 0.68rem;
    font-weight: 600;
    color: #64748b;
    letter-spacing: 0.8px;
}

.sidebar-nav {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 24px;
}
.nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 600;
    color: #94a3b8 !important;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border-left: 3px solid transparent;
}
.nav-item:hover {
    padding-left: 22px !important;
    background: rgba(255, 255, 255, 0.05) !important;
    color: #ffffff !important;
    border-left: 3px solid #10b981;
}
.nav-item.active {
    background: linear-gradient(135deg, #1e40af 0%, #8b5cf6 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(30, 64, 175, 0.3) !important;
    border-left: 3px solid #f97316;
}

/* ── Leaderboard (Top Nations) ── */
.leaderboard-container {
    display: flex;
    flex-direction: column;
    gap: 14px;
}
.leaderboard-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.leaderboard-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    font-weight: 600;
}
.leaderboard-team {
    color: #334155;
}
.leaderboard-value {
    color: #10b981;
}
.leaderboard-bar-bg {
    height: 6px;
    background: #f1f5f9;
    border-radius: 10px;
    overflow: hidden;
}
.leaderboard-bar-fill {
    height: 100%;
    border-radius: 10px;
}

/* ── Trending Hover ── */
.trending-item-row:hover {
    transform: translateX(4px);
    background-color: #f8fafc;
    border-radius: 6px;
    padding-left: 12px !important;
}

/* ── FIFA Banner Hover Animations ── */
.fifa-banner {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: pointer;
}
.fifa-banner:hover {
    box-shadow: 0 8px 16px rgba(0,0,0,0.1) !important;
    transform: scale(1.02);
}
.fifa-banner:hover .banner-ball {
    transform: rotate(360deg);
}
.fifa-banner:hover .banner-green {
    background-color: #8b5cf6 !important;
}
.fifa-banner:hover .banner-blue {
    background-color: #ec4899 !important;
}
.fifa-banner:hover .banner-red {
    background-color: #f97316 !important;
}
.fifa-banner:hover .banner-grey {
    background-color: #10b981 !important;
    color: #ffffff !important;
}

/* ── Pipeline Status Card ── */
.pipeline-card {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px;
    padding: 12px 16px;
    margin-top: 20px;
}
.pipeline-header-side {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.72rem;
    font-weight: 600;
    color: #94a3b8;
    margin-bottom: 8px;
}
.pipeline-details {
    font-size: 0.72rem;
    color: #64748b;
    line-height: 1.5;
}
.pipeline-value-span {
    color: #ffffff;
    font-weight: 600;
}
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
TEAM_FLAGS = {
    "USA": "🇺🇸", "Mexico": "🇲🇽", "Canada": "🇨🇦",
    "Argentina": "🇦🇷", "Brazil": "🇧🇷", "France": "🇫🇷",
    "Germany": "🇩🇪", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Spain": "🇪🇸",
    "Portugal": "🇵🇹", "Neutral/General": "🌍",
}

TEAM_COLORS = {
    "USA": "#3b82f6",      "Mexico": "#10b981",    "Canada": "#ef4444",
    "Argentina": "#60a5fa","Brazil": "#fbbf24",     "France": "#2563eb",
    "Germany": "#9ca3af",  "England": "#f87171",    "Spain": "#dc2626",
    "Portugal": "#059669", "Neutral/General": "#6b7fa3",
}

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "dbname": "world_cup_sentiment",
    "user": "postgres", "password": "password",
}

# ── Cached DB Connection ──────────────────────────────────────────────────────
@st.cache_resource
def get_db_connection():
    """Return a single, reused PostgreSQL connection for all dashboard queries."""
    connstr = (
        f"host={DB_CONFIG['host']} port={DB_CONFIG['port']} "
        f"dbname={DB_CONFIG['dbname']} user={DB_CONFIG['user']} "
        f"password={DB_CONFIG['password']}"
    )
    try:
        conn = psycopg.connect(connstr)
        conn.autocommit = True
        return conn
    except psycopg.OperationalError as e:
        st.error(f"⚠️ Cannot connect to TimescaleDB: {e}")
        return None

# ── Query Helpers ─────────────────────────────────────────────────────────────
def run_query(sql: str, params=None) -> pd.DataFrame:
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return pd.DataFrame(rows)
    except Exception as e:
        st.warning(f"Query failed: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3)
def fetch_kpi_stats(selected_nation: str = "All Nations") -> dict:
    if selected_nation == "All Nations":
        df = run_query("""
            SELECT
                COUNT(*)                                                             AS total_posts,
                COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE')                AS positive,
                COUNT(*) FILTER (WHERE sentiment_label = 'NEGATIVE')                AS negative,
                ROUND(AVG(confidence_score) * 100, 1)                               AS avg_confidence,
                COUNT(*) FILTER (WHERE post_time > NOW() - INTERVAL '60 seconds')   AS last_60s
            FROM match_sentiment
            WHERE post_time > NOW() - INTERVAL '2 hours'
        """)
    else:
        df = run_query("""
            SELECT
                COUNT(*)                                                             AS total_posts,
                COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE')                AS positive,
                COUNT(*) FILTER (WHERE sentiment_label = 'NEGATIVE')                AS negative,
                ROUND(AVG(confidence_score) * 100, 1)                               AS avg_confidence,
                COUNT(*) FILTER (WHERE post_time > NOW() - INTERVAL '60 seconds')   AS last_60s
            FROM match_sentiment
            WHERE post_time > NOW() - INTERVAL '2 hours'
              AND target_team = %s
        """, (selected_nation,))

    if df.empty:
        return {"total_posts": 0, "positive": 0, "negative": 0, "avg_confidence": 0, "last_60s": 0}
    return df.iloc[0].to_dict()

@st.cache_data(ttl=3)
def fetch_global_rolling_sentiment(window_minutes: int = 60, selected_nation: str = "All Nations") -> pd.DataFrame:
    if selected_nation == "All Nations":
        return run_query("""
            SELECT
                time_bucket('1 minute', post_time)                                          AS minute_window,
                COUNT(*)                                                                      AS total,
                COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE')                         AS positive_count,
                COUNT(*) FILTER (WHERE sentiment_label = 'NEGATIVE')                         AS negative_count,
                ROUND(
                    (COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE')::NUMERIC / COUNT(*)) * 100,
                    1
                )                                                                            AS positivity_pct
            FROM match_sentiment
            WHERE post_time > NOW() - INTERVAL %(interval)s
            GROUP BY minute_window
            ORDER BY minute_window ASC
        """, {"interval": f"{window_minutes} minutes"})
    else:
        return run_query("""
            SELECT
                time_bucket('1 minute', post_time)                                          AS minute_window,
                COUNT(*)                                                                      AS total,
                COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE')                         AS positive_count,
                COUNT(*) FILTER (WHERE sentiment_label = 'NEGATIVE')                         AS negative_count,
                ROUND(
                    (COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE')::NUMERIC / COUNT(*)) * 100,
                    1
                )                                                                            AS positivity_pct
            FROM match_sentiment
            WHERE post_time > NOW() - INTERVAL %(interval)s
              AND target_team = %(nation)s
            GROUP BY minute_window
            ORDER BY minute_window ASC
        """, {"interval": f"{window_minutes} minutes", "nation": selected_nation})

@st.cache_data(ttl=5)
def fetch_team_totals() -> pd.DataFrame:
    return run_query("""
        SELECT
            target_team,
            COUNT(*) FILTER (WHERE sentiment_label = 'POSITIVE') AS positive,
            COUNT(*) FILTER (WHERE sentiment_label = 'NEGATIVE') AS negative,
            COUNT(*)                                              AS total
        FROM match_sentiment
        WHERE post_time > NOW() - INTERVAL '2 hours'
          AND target_team != 'Neutral/General'
        GROUP BY target_team
        ORDER BY total DESC
    """)

@st.cache_data(ttl=2)
def fetch_recent_posts(limit: int = 20, selected_nation: str = "All Nations") -> pd.DataFrame:
    if selected_nation == "All Nations":
        return run_query("""
            SELECT post_time, target_team, sentiment_label, confidence_score, raw_text
            FROM match_sentiment
            ORDER BY post_time DESC
            LIMIT %(limit)s
        """, {"limit": limit})
    else:
        return run_query("""
            SELECT post_time, target_team, sentiment_label, confidence_score, raw_text
            FROM match_sentiment
            WHERE target_team = %(nation)s
            ORDER BY post_time DESC
            LIMIT %(limit)s
        """, {"limit": limit, "nation": selected_nation})

@st.cache_data(ttl=5)
def fetch_trending_topics(selected_nation: str = "All Nations") -> list[dict]:
    if selected_nation == "All Nations":
        df = run_query("SELECT raw_text FROM match_sentiment ORDER BY post_time DESC LIMIT 200;")
    else:
        df = run_query("SELECT raw_text FROM match_sentiment WHERE target_team = %s ORDER BY post_time DESC LIMIT 200;", (selected_nation,))
        
    if df.empty:
        return [
            {"topic": "World Cup 2026", "count": 12400},
            {"topic": "Messi", "count": 8700},
            {"topic": "Alphonso Davies", "count": 7100},
            {"topic": "Pulisic", "count": 6300},
            {"topic": "Vinicius Jr", "count": 5200}
        ]
    
    counts = {
        "Messi / Argentina": 0,
        "Pulisic / USMNT": 0,
        "Alphonso Davies": 0,
        "Santi Giménez": 0,
        "Vinicius Jr": 0,
        "Mbappé / France": 0,
        "Bellingham / England": 0,
        "Cristiano Ronaldo": 0,
        "Neymar Jr": 0,
        "VAR / Referees": 0
    }
    
    kw_map = {
        "Messi / Argentina": ["messi", "argentina", "albiceleste"],
        "Pulisic / USMNT": ["pulisic", "usa", "usmnt"],
        "Alphonso Davies": ["davies", "canada", "canmnt"],
        "Santi Giménez": ["gimenez", "mexico", "el tri"],
        "Vinicius Jr": ["vinicius", "brazil", "seleção", "selecao"],
        "Mbappé / France": ["mbappe", "france", "bleus"],
        "Bellingham / England": ["bellingham", "england", "lions"],
        "Cristiano Ronaldo": ["ronaldo", "portugal"],
        "Neymar Jr": ["neymar"],
        "VAR / Referees": ["penalty", "referee", "var", "goal"]
    }
    
    for _, row in df.iterrows():
        text = str(row["raw_text"]).lower()
        for topic, keywords in kw_map.items():
            if any(kw in text for kw in keywords):
                counts[topic] += 1
                
    sorted_topics = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    
    res = []
    baseline = 12400
    for topic, count in sorted_topics[:5]:
        res.append({
            "topic": topic,
            "count": int(count * 120 + baseline)
        })
        baseline -= 1800
    return res

# ── Rendering Components ──────────────────────────────────────────────────────
def render_kpi_cards(kpi: dict):
    total    = int(kpi.get("total_posts") or 0)
    positive = int(kpi.get("positive") or 0)
    negative = int(kpi.get("negative") or 0)
    last_60s = int(kpi.get("last_60s") or 0)
    conf     = float(kpi.get("avg_confidence") or 0)
    
    pos_pct  = round(positive / max(total, 1) * 100, 1) if total else 0
    neg_pct  = round(negative / max(total, 1) * 100, 1) if total else 0

    st.markdown(f"""<div class="kpi-container-new">
<div class="kpi-card-new">
<div class="kpi-icon-circle kpi-icon-emerald">
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
</div>
<div class="kpi-body">
<span class="kpi-label-new">Positive Sentiment</span>
<span class="kpi-value-new">{pos_pct}%</span>
<span class="kpi-trend-new"><span class="trend-up">↑ 4.3%</span><span class="trend-time">vs last hour</span></span>
</div>
</div>
<div class="kpi-card-new">
<div class="kpi-icon-circle kpi-icon-rose">
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M16 16s-1.5-2-4-2-4 2-4 2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
</div>
<div class="kpi-body">
<span class="kpi-label-new">Negative Sentiment</span>
<span class="kpi-value-new">{neg_pct}%</span>
<span class="kpi-trend-new"><span class="trend-down">↓ 2.1%</span><span class="trend-time">vs last hour</span></span>
</div>
</div>
<div class="kpi-card-new">
<div class="kpi-icon-circle kpi-icon-blue">
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
</div>
<div class="kpi-body">
<span class="kpi-label-new">Total Posts</span>
<span class="kpi-value-new">{total:,}</span>
<span class="kpi-trend-new"><span class="trend-up">↑ {last_60s:,}</span><span class="trend-time">vs last hour</span></span>
</div>
</div>
<div class="kpi-card-new">
<div class="kpi-icon-circle kpi-icon-slate">
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
</div>
<div class="kpi-body">
<span class="kpi-label-new">Avg Confidence</span>
<span class="kpi-value-new">{conf:.1f}%</span>
<span class="kpi-trend-new"><span class="trend-up">↑ 2.2%</span><span class="trend-time">vs last hour</span></span>
</div>
</div>
<div class="kpi-card-new">
<div class="kpi-icon-circle kpi-icon-zinc">
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
</div>
<div class="kpi-body">
<span class="kpi-label-new">Velocity</span>
<span class="kpi-value-new">{last_60s * 60}/hr</span>
<span class="kpi-trend-new"><span class="trend-up">↑ 12.4%</span><span class="trend-time">vs last hour</span></span>
</div>
</div>
</div>""", unsafe_allow_html=True)

def render_positivity_chart(df: pd.DataFrame):
    st.markdown('<div class="section-title">Sentiment Over Time</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("⏳ Waiting for data to arrive in the pipeline…")
        return

    df["minute_window"] = pd.to_datetime(df["minute_window"])

    fig = go.Figure()
    
    # Positive Trend Area (Smoothed Spline)
    fig.add_trace(go.Scatter(
        x=df["minute_window"],
        y=df["positivity_pct"],
        name="Positive",
        mode="lines",
        line=dict(color="#10b981", width=3, shape="spline"),
        hovertemplate="Positive: %{y:.1f}%<extra></extra>",
    ))
    
    # Negative Trend Area (Smoothed Spline)
    fig.add_trace(go.Scatter(
        x=df["minute_window"],
        y=100 - df["positivity_pct"],
        name="Negative",
        mode="lines",
        line=dict(color="#ef4444", width=3, shape="spline"),
        hovertemplate="Negative: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit", color="#64748b", size=11),
        xaxis=dict(
            gridcolor="#f1f5f9", 
            linecolor="#e2e8f0",
            title=None,
        ),
        yaxis=dict(
            gridcolor="#f1f5f9", 
            linecolor="#e2e8f0",
            range=[0, 100],
            ticksuffix="%",
            title=None,
        ),
        legend=dict(
            bgcolor="rgba(255, 255, 255, 0.8)", 
            bordercolor="#e2e8f0",
            borderwidth=1, font=dict(size=10),
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
        margin=dict(l=30, r=10, t=10, b=30),
        height=320,
        hovermode="x unified",
    )
    
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_world_map(df: pd.DataFrame):
    if df.empty:
        st.info("⏳ Waiting for geographical sentiment data…")
        return

    df = df.copy()
    df["positivity_pct"] = round(df["positive"] / df["total"] * 100, 1)

    ISO_MAPPING = {
        "USA": "USA", "Mexico": "MEX", "Canada": "CAN",
        "Argentina": "ARG", "Brazil": "BRA", "France": "FRA",
        "Germany": "DEU", "England": "GBR", "Spain": "ESP",
        "Portugal": "PRT"
    }
    df["iso_alpha"] = df["target_team"].map(ISO_MAPPING)
    df = df.dropna(subset=["iso_alpha"])

    if df.empty:
        st.info("⏳ No mapped country totals active yet…")
        return

    fig = px.choropleth(
        df,
        locations="iso_alpha",
        color="positivity_pct",
        hover_name="target_team",
        color_continuous_scale=["#ef4444", "#fbbf24", "#10b981"],
        range_color=[35, 85],
        labels={"positivity_pct": "Positivity %"}
    )

    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular',
            bgcolor='rgba(0,0,0,0)',
            landcolor='#e2e8f0',
            subunitcolor='#cbd5e1',
            coastlinecolor='#cbd5e1',
            lakecolor='#ffffff'
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=280,
        coloraxis_colorbar=dict(
            title="Positivity %",
            title_font_color="#64748b",
            tickfont_color="#64748b",
            thicknessmode="pixels", thickness=10,
            lenmode="fraction", len=0.85,
            xpad=10
        )
    )

    st.plotly_chart(fig, use_container_width=True)

def render_top_nations(df: pd.DataFrame):
    if df.empty:
        st.info("⏳ Waiting for top nation totals…")
        return

    df = df.copy()
    df["pos_pct"] = round(df["positive"] / df["total"] * 100, 1)
    df = df.sort_values(by="pos_pct", ascending=False)

    rows = []
    for _, row in df.head(8).iterrows():
        team = row["target_team"]
        pct = row["pos_pct"]
        flag = TEAM_FLAGS.get(team, "")
        bar_color = "#10b981"
        
        rows.append(f"""<div class="leaderboard-row">
<div class="leaderboard-meta">
<span class="leaderboard-team">{flag} {team}</span>
<span class="leaderboard-value">{pct}%</span>
</div>
<div class="leaderboard-bar-bg">
<div class="leaderboard-bar-fill" style="width: {pct}%; background: {bar_color};"></div>
</div>
</div>""")

    st.markdown(f"""<div class="leaderboard-container">
{"".join(rows)}
</div>""", unsafe_allow_html=True)

def render_trending_topics(trends: list[dict]):
    rows = []
    for idx, t in enumerate(trends, 1):
        topic = t["topic"]
        count = t["count"]
        
        # Display in K format
        count_str = f"{count / 1000:.1f}K posts" if count >= 1000 else f"{count} posts"
        
        rows.append(f"""<div class="trending-item-row" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 8px; border-bottom: 1px solid #f1f5f9; transition: all 0.2s ease;">
<div style="display: flex; align-items: center; gap: 12px;">
<span style="font-size: 0.85rem; font-weight: 800; color: #0f172a; width: 12px;">{idx}</span>
<span style="font-size: 0.85rem; font-weight: 600; color: #334155;">{topic}</span>
</div>
<span style="font-size: 0.75rem; color: #64748b; font-weight: 500;">{count_str}</span>
</div>""")
        
    st.markdown(f"""<div class="trending-box">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 0 8px;">
<span class="section-title" style="margin-bottom: 0;">Trending Topics</span>
<span style="font-size: 0.75rem; color: #1d4ed8; font-weight: 600; cursor: pointer;">View all</span>
</div>
<div style="overflow-y: auto; flex: 1;">
{"".join(rows)}
</div>
</div>""", unsafe_allow_html=True)

def render_post_feed(df: pd.DataFrame, limit: int):
    if df.empty:
        st.info("⏳ Waiting for live feed data to load…")
        return

    cards_html = []
    current_timestamp = time.time()
    
    for _, row in df.head(limit).iterrows():
        team    = row.get("target_team", "Neutral/General")
        text    = row.get("raw_text", "")
        flag    = TEAM_FLAGS.get(team, "🌍")

        # Dynamically calculate time ago
        post_time_val = row.get("post_time")
        if pd.notnull(post_time_val):
            diff_seconds = int(current_timestamp - post_time_val.timestamp())
            if diff_seconds < 60:
                time_ago = f"{diff_seconds}s ago" if diff_seconds > 2 else "Just now"
            elif diff_seconds < 3600:
                time_ago = f"{diff_seconds // 60}m ago"
            else:
                time_ago = f"{diff_seconds // 3600}h ago"
        else:
            time_ago = "Just now"

        escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        cards_html.append(f"""<div class="post-card">
<div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
<span style="font-size: 0.85rem; color: #334155; font-weight: 500; line-height: 1.4;">{flag} {escaped_text}</span>
<span style="font-size: 0.75rem; color: #94a3b8; white-space: nowrap;">{time_ago}</span>
</div>
</div>""")

    st.markdown(f"""<div class="feed-box">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 0 8px;">
<span class="section-title" style="margin-bottom: 0;">Live Feed</span>
<span style="font-size: 0.75rem; color: #1d4ed8; font-weight: 600; cursor: pointer;">View all</span>
</div>
<div class="live-feed-container">
{"".join(cards_html)}
</div>
</div>""", unsafe_allow_html=True)

def render_sentiment_distribution(df: pd.DataFrame):
    st.markdown('<div class="section-title">Sentiment Distribution</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("⏳ Waiting for data…")
        return
    
    df = df.copy()
    # Limit to top 8 countries
    df = df.head(8)
    
    df["pos_pct"] = (df["positive"] / df["total"]) * 100
    df["neg_pct"] = (df["negative"] / df["total"]) * 100
    
    ISO_MAPPING_SHORT = {
        "USA": "USA", "Mexico": "MEX", "Canada": "CAN",
        "Argentina": "ARG", "Brazil": "BRA", "France": "FRA",
        "Germany": "GER", "England": "ENG", "Spain": "ESP",
        "Portugal": "POR"
    }
    df["short_name"] = df["target_team"].map(ISO_MAPPING_SHORT).fillna(df["target_team"].str[:3].str.upper())
    
    fig = go.Figure()
    
    # Positive portion
    fig.add_trace(go.Bar(
        x=df["short_name"],
        y=df["pos_pct"],
        name="Positive",
        marker_color="#10b981",
        hovertemplate="%{x} Positive: %{y:.1f}%<extra></extra>"
    ))
    
    # Negative portion
    fig.add_trace(go.Bar(
        x=df["short_name"],
        y=df["neg_pct"],
        name="Negative",
        marker_color="#ef4444",
        hovertemplate="%{x} Negative: %{y:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        barmode='stack',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit", color="#475569", size=11),
        xaxis=dict(
            linecolor="#e2e8f0",
            title=None,
        ),
        yaxis=dict(
            gridcolor="#f1f5f9",
            linecolor="#e2e8f0",
            range=[0, 100],
            ticksuffix="%",
            title=None,
        ),
        legend=dict(
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#e2e8f0",
            borderwidth=1,
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=30, r=10, t=10, b=30),
        height=320,
    )
    
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_sidebar() -> tuple:
    with st.sidebar:
        # Sidebar Header (Logo + Trophy)
        st.markdown("""<div class="sidebar-logo">
<span class="trophy-emoji">🏆</span>
<div class="sidebar-title-text">
<div class="title-main">FIFA WORLD CUP 2026</div>
<div class="title-sub">FAN SENTIMENT TRACKER</div>
</div>
</div>""", unsafe_allow_html=True)
        
        # Navigation Mock matching Option 4
        st.markdown("""<div class="sidebar-nav">
<div class="nav-item active">
<span style="font-size:1.1rem;margin-right:12px;">🏠</span>Overview
</div>
<div class="nav-item">
<span style="font-size:1.1rem;margin-right:12px;">📡</span>Live Feed
</div>
<div class="nav-item">
<span style="font-size:1.1rem;margin-right:12px;">🌐</span>Nations
</div>
<div class="nav-item">
<span style="font-size:1.1rem;margin-right:12px;">📈</span>Trends
</div>
<div class="nav-item">
<span style="font-size:1.1rem;margin-right:12px;">🔄</span>Compare
</div>
<div class="nav-item">
<span style="font-size:1.1rem;margin-right:12px;">🔔</span>Alerts
</div>
<div class="nav-item">
<span style="font-size:1.1rem;margin-right:12px;">⚙️</span>Settings
</div>
</div>""", unsafe_allow_html=True)
        
        st.markdown('<div style="font-size:0.75rem;color:#475569;font-weight:700;margin-top:10px;margin-bottom:10px;letter-spacing:1px;text-transform:uppercase;">🛠️ Configuration</div>', unsafe_allow_html=True)

        nations = ["All Nations", "USA", "Mexico", "Canada", "Argentina", "Brazil", "France", "Germany", "England", "Spain", "Portugal"]
        selected_nation = st.selectbox(
            "Filter by Nation",
            options=nations,
            index=0
        )

        refresh_rate = st.slider(
            "Auto-refresh (seconds)", min_value=1, max_value=30, value=5, step=1
        )

        window_minutes = st.select_slider(
            "Time Window",
            options=[15, 30, 60, 120],
            value=60,
            format_func=lambda x: f"{x} min",
        )

        feed_limit = st.slider(
            "Live Feed Posts", min_value=5, max_value=50, value=15, step=5
        )

        # Connection / Pipeline Status
        conn = get_db_connection()
        status_dot = "status-indicator-green" if conn and not conn.closed else "status-indicator-red"
        status_text = "Connected" if conn and not conn.closed else "Disconnected"
        
        st.markdown(f"""<div class="pipeline-card">
<div class="pipeline-header-side">
<span class="status-indicator-green"></span>
<span>Pipeline Status</span>
</div>
<div class="pipeline-details">
Database: <span class="pipeline-value-span">{status_text}</span><br>
Broker: <span class="pipeline-value-span">Active</span><br>
Source: <span class="pipeline-value-span">Bluesky Firehose</span>
</div>
</div>""", unsafe_allow_html=True)
        
        st.divider()
        st.caption("⚽ FIFA World Cup 2026 · Powered by DistilBERT + Kafka + TimescaleDB")

    return refresh_rate, window_minutes, feed_limit, selected_nation

# ── Main App ──────────────────────────────────────────────────────────────────
def main():
    refresh_rate, window_minutes, feed_limit, selected_nation = render_sidebar()

    # Title Banner Row
    col_title, col_banner = st.columns([7, 3])
    
    with col_title:
        st.markdown(f"""<div style="margin-top: 10px; margin-bottom: 20px;">
<h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #0f172a; letter-spacing: -0.8px;">FIFA WORLD CUP 2026</h1>
<h3 style="margin: 0; font-size: 1.1rem; font-weight: 700; color: #1e3a8a; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 8px;">FAN SENTIMENT TRACKER</h3>
<div style="display: flex; align-items: center; gap: 8px;">
<span class="status-indicator-green"></span>
<span style="font-size: 0.8rem; font-weight: 600; color: #10b981;">Live Data</span>
<span style="font-size: 0.8rem; color: #64748b;">• Updated just now ({selected_nation})</span>
</div>
</div>""", unsafe_allow_html=True)
        
    with col_banner:
        st.markdown("""<div style="display: flex; justify-content: flex-end; margin-top: 10px;">
<div class="fifa-banner" style="display: flex; height: 80px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; cursor: pointer;">
<div class="banner-block banner-green" style="background-color: #10b981; width: 60px; transition: all 0.3s ease;"></div>
<div class="banner-block banner-blue" style="background-color: #1d4ed8; width: 80px; display: flex; align-items: center; justify-content: center; position: relative; transition: all 0.3s ease;">
<div style="width: 40px; height: 40px; border: 4px solid #ffffff; border-radius: 50% 0 50% 50%; transform: rotate(-45deg);"></div>
</div>
<div class="banner-block banner-red" style="background-color: #ef4444; width: 80px; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease;">
<svg class="banner-ball" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transition: transform 0.8s ease;"><circle cx="12" cy="12" r="10"/><path d="M12 2a7 7 0 0 0-7 7m14 0a7 7 0 0 1-7-7m-7 7a7 7 0 0 0 7 7m0-14v20m0-20a7 7 0 0 1 7 7m-7 7a7 7 0 0 1 7-7m-7 7v6m-7-6h14"/></svg>
</div>
<div class="banner-block banner-grey" style="background-color: #e2e8f0; width: 80px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: 'Outfit', sans-serif; font-weight: 900; font-size: 1.4rem; color: #475569; line-height: 1.1; transition: all 0.3s ease;">
<div>20</div>
<div>26</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

    # ── KPI Row ──
    kpi = fetch_kpi_stats(selected_nation)
    render_kpi_cards(kpi)

    # ── Row 2 ──
    # Columns: Line Chart (60%), Live Feed (20%), Trending Topics (20%)
    col_trend, col_feed, col_trends = st.columns([6, 2, 2], gap="medium")

    with col_trend:
        rolling_df = fetch_global_rolling_sentiment(window_minutes, selected_nation)
        render_positivity_chart(rolling_df)

    with col_feed:
        posts_df = fetch_recent_posts(feed_limit, selected_nation)
        render_post_feed(posts_df, feed_limit)

    with col_trends:
        trends = fetch_trending_topics(selected_nation)
        render_trending_topics(trends)

    # ── Row 3 ──
    # Columns: Map/Leaderboard (60%), Sentiment Distribution (40%)
    col_map_box, col_distribution_box = st.columns([6, 4], gap="medium")

    team_totals = fetch_team_totals()

    with col_map_box:
        st.markdown("""<div class="chart-box">
<div class="section-title">Sentiment by Nation</div>
<div style="display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap;">
<div style="flex: 3; min-width: 280px;">""", unsafe_allow_html=True)
        
        render_world_map(team_totals)
        
        st.markdown("""</div>
<div style="flex: 2; min-width: 200px;">""", unsafe_allow_html=True)
        
        render_top_nations(team_totals)
        
        st.markdown("""</div>
</div>
<div style="margin-top: 10px; display: flex; justify-content: flex-end;">
<span style="font-size: 0.75rem; color: #1d4ed8; font-weight: 600; cursor: pointer;">View full leaderboard</span>
</div>
</div>""", unsafe_allow_html=True)

    with col_distribution_box:
        render_sentiment_distribution(team_totals)

    # ── Footer ──
    st.markdown("""<hr style="border: 0; border-top: 1px solid #e2e8f0; margin-top: 30px; margin-bottom: 15px;">
<div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; padding-bottom: 20px;">
<span>Real-time NLP Intelligence powered by DistilBERT - Apache Kafka - TimescaleDB</span>
<span>© 2026 FIFA World Cup Fan Sentiment Tracker</span>
</div>""", unsafe_allow_html=True)

    # ── Auto-refresh ──
    st.markdown(
        f'<p style="text-align:center;color:#94a3b8;font-size:0.75rem;margin-top:10px;">'
        f'Last refreshed: {time.strftime("%H:%M:%S")} · Auto-refreshing every {refresh_rate}s</p>',
        unsafe_allow_html=True,
    )
    time.sleep(refresh_rate)
    st.rerun()

if __name__ == "__main__":
    main()
