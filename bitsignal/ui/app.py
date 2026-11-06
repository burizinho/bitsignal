"""Interactive local Streamlit dashboard for BitSignal."""

import os
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DB_PATH = os.getenv("DATABASE_PATH", "./data/bitsignal.db")

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


def ensure_data_available():
    """Ensure data is loaded; compute immediately if running fresh on Streamlit Cloud."""
    df_scores, df_metrics, df_alerts = load_data()
    if df_scores is None or df_scores.empty:
        with st.spinner("Inicializando dados de mercado ao vivo na nuvem..."):
            from bitsignal.cli import cmd_run_daily
            import argparse
            cmd_run_daily(argparse.Namespace(db_path=DB_PATH, dry_run=True))
            df_scores, df_metrics, df_alerts = load_data()
    return df_scores, df_metrics, df_alerts


st.title("⚡ BitSignal: Bitcoin Macro Cycle Sentinel")
st.caption("Autonomous Quantitative Macro Cycle & Cold Storage Divestment Monitor")

# Sidebar controls
with st.sidebar:
    st.header("Controles")
    if st.button("🔄 Atualizar Dados Agora"):
        with st.spinner("Consultando APIs on-chain e de mercado..."):
            from bitsignal.cli import cmd_run_daily
            import argparse
            cmd_run_daily(argparse.Namespace(db_path=DB_PATH, dry_run=True))
            st.success("Dados atualizados com sucesso!")
            st.rerun()

df_scores, df_metrics, df_alerts = ensure_data_available()

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
