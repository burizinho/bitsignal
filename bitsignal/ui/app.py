"""Interactive local Streamlit dashboard for BitSignal."""

import argparse
import os
import sqlite3
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Ensure repository root is in sys.path (needed for Streamlit Cloud deployment)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_DB_PATH = str(ROOT_DIR / "data" / "bitsignal.db")
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)

st.set_page_config(
    page_title="BitSignal - Bitcoin Macro Cycle Sentinel",
    page_icon="⚡",
    layout="wide",
)


def load_data():
    if not os.path.exists(DB_PATH):
        return None, None, None
    conn = sqlite3.connect(DB_PATH)
    try:
        df_scores = pd.read_sql_query("SELECT * FROM daily_scores ORDER BY date ASC;", conn)
        df_metrics = pd.read_sql_query("SELECT * FROM daily_metrics ORDER BY date ASC;", conn)
        df_alerts = pd.read_sql_query("SELECT * FROM alert_dispatches ORDER BY date DESC LIMIT 20;", conn)
        return df_scores, df_metrics, df_alerts
    except Exception:
        return None, None, None
    finally:
        conn.close()


from datetime import datetime, timezone

AUTO_REFRESH_SECONDS = int(os.getenv("AUTO_REFRESH_SECONDS", 3600))  # 1 hour default


def is_data_stale(df_scores) -> bool:
    """Return True if no data exists or the newest score is older than AUTO_REFRESH_SECONDS (1 hour)."""
    if df_scores is None or df_scores.empty:
        return True
    try:
        latest = df_scores.iloc[-1]
        ts_str = latest.get("created_at")
        if not ts_str or pd.isna(ts_str):
            return True
        ts = pd.to_datetime(ts_str, utc=True)
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds() >= AUTO_REFRESH_SECONDS
    except Exception:
        return False


def ensure_data_available():
    """Ensure data is loaded; automatically updates if data is missing or older than 1 hour."""
    df_scores, df_metrics, df_alerts = load_data()
    if is_data_stale(df_scores):
        is_empty = df_scores is None or df_scores.empty
        msg = "Inicializando dados de mercado ao vivo..." if is_empty else "Atualizando indicadores de mercado (dados com mais de 1h)..."
        with st.spinner(msg):
            try:
                from bitsignal.cli import cmd_run_daily
                cmd_run_daily(argparse.Namespace(db_path=DB_PATH, dry_run=True))
                fresh_scores, fresh_metrics, fresh_alerts = load_data()
                if fresh_scores is not None and not fresh_scores.empty:
                    df_scores, df_metrics, df_alerts = fresh_scores, fresh_metrics, fresh_alerts
            except Exception as exc:
                if is_empty:
                    st.error(f"Erro ao inicializar dados na nuvem: {exc}")
                else:
                    st.warning(f"Não foi possível buscar os dados mais recentes agora ({exc}). Exibindo último registro em cache.")
    return df_scores, df_metrics, df_alerts


df_scores, df_metrics, df_alerts = ensure_data_available()

st.title("⚡ BitSignal: Bitcoin Macro Cycle Sentinel")
st.caption("Autonomous Quantitative Macro Cycle & Cold Storage Divestment Monitor")

# Sidebar controls
with st.sidebar:
    st.header("Controles")
    if df_scores is not None and not df_scores.empty:
        last_updated = df_scores.iloc[-1].get("created_at", "N/A")
        st.caption(f"🕒 **Última atualização:**\n`{last_updated} UTC`")
        st.caption("🔄 *Auto-refresh a cada 1 hora ao abrir.*")
    if st.button("🔄 Atualizar Dados Agora"):
        with st.spinner("Consultando APIs on-chain e de mercado..."):
            try:
                from bitsignal.cli import cmd_run_daily
                cmd_run_daily(argparse.Namespace(db_path=DB_PATH, dry_run=True))
                st.success("Dados atualizados com sucesso!")
                st.rerun()
            except Exception as exc:
                st.error(f"Erro ao atualizar dados: {exc}")

if df_scores is None or df_scores.empty:
    st.warning("No data found in database. Please run `bitsignal run-daily` or `bitsignal db-init` first.")
    st.stop()

latest_score = df_scores.iloc[-1]
latest_metric = df_metrics.iloc[-1] if df_metrics is not None and not df_metrics.empty else None

col1, col2, col3, col4 = st.columns(4)
score_val = float(latest_score["composite_score"])
status_val = latest_score["system_status"]
hysteresis_val = latest_score["hysteresis_state"]
btc_price = float(latest_metric["btc_price"]) if latest_metric is not None else 0.0

col1.metric("Composite Cycle Score", f"{score_val:.1f} / 100")
col2.metric("Market Price (BTC)", f"${btc_price:,.2f}")
col3.metric("System Health", status_val)
col4.metric("Hysteresis Regime", hysteresis_val)

st.markdown("---")

# Layout: Gauge on Left, Waterfall on Right
c_left, c_right = st.columns([1, 1])

with c_left:
    st.subheader("Macro Cycle Regime Gauge")
    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score_val,
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "white"},
                "bar": {"color": "black", "thickness": 0.25},
                "steps": [
                    {"range": [0, 20], "color": "#00CC96"},  # Green Bottom
                    {"range": [20, 80], "color": "#636EFA"},  # Neutral
                    {"range": [80, 85], "color": "#FFA15A"},  # Tier 1 Top
                    {"range": [85, 90], "color": "#FF6692"},  # Tier 2 Top
                    {"range": [90, 100], "color": "#EF553B"},  # Tier 3 Mania
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": score_val,
                },
            },
        )
    )
    fig_gauge.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

with c_right:
    st.subheader("Indicator Point Attribution")
    indicators = ["MVRV Z (25%)", "200w SMA (20%)", "Puell (20%)", "Pi Cycle (15%)", "Weekly RSI (10%)", "Hash Ribbon (10%)"]
    points = [
        float(latest_score["mvrv_score"]) * 0.25,
        float(latest_score["sma200w_score"]) * 0.20,
        float(latest_score["puell_score"]) * 0.20,
        float(latest_score["picycle_score"]) * 0.15,
        float(latest_score["rsi_score"]) * 0.10,
        float(latest_score["hashribbon_score"]) * 0.10,
    ]
    fig_waterfall = go.Figure(
        go.Bar(
            x=indicators,
            y=points,
            text=[f"{p:.1f} pts" for p in points],
            textposition="auto",
            marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"],
        )
    )
    fig_waterfall.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20), yaxis=dict(title="Points Contributed"))
    st.plotly_chart(fig_waterfall, use_container_width=True)

# Historical Time-Series
st.subheader("Historical Trajectory & Cycle Bands")
fig_history = go.Figure()

fig_history.add_trace(
    go.Scatter(
        x=df_scores["date"],
        y=df_scores["composite_score"],
        mode="lines",
        name="Composite Score",
        line=dict(color="#636EFA", width=2.5),
    )
)
fig_history.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Tier 1 Top (80)")
fig_history.add_hline(y=20, line_dash="dash", line_color="green", annotation_text="Capitulation Bottom (20)")
fig_history.update_layout(
    height=400,
    xaxis_title="Date",
    yaxis_title="Score (0-100)",
    yaxis=dict(range=[0, 100]),
    margin=dict(l=20, r=20, t=30, b=20),
)
st.plotly_chart(fig_history, use_container_width=True)

# Alert Audit Log
if df_alerts is not None and not df_alerts.empty:
    st.subheader("Recent Alert Dispatch History")
    st.dataframe(df_alerts[["date", "alert_type", "composite_score", "delivered_telegram", "created_at"]], use_container_width=True)
