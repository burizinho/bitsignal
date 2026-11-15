"""Plotly charts for the new dashboard (plan item 36).

No constants of their own: thresholds and limits come from the config and the replay result.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import pandas as pd
import plotly.graph_objects as go

from bitsignal.models import Event, EventType, Phase

PHASE_COLORS = {
    Phase.ACCUMULATE.value: "rgba(0, 168, 107, 0.20)",
    Phase.HOLD.value: "rgba(108, 117, 125, 0.08)",
    Phase.DISTRIBUTE.value: "rgba(232, 93, 4, 0.20)",
}


def score_gauge(score: float, ladder: Sequence[Tuple[float, float]], arm_score: float, title: str = "Score de valuation") -> go.Figure:
    """0–100 gauge with the buy zone (<= arm score) and the sell ladder steps shaded."""
    steps = [{"range": [0, arm_score], "color": "#00A86B"}]
    thresholds = [t for t, _ in ladder]
    edges = [arm_score, thresholds[0]] if thresholds else [arm_score, 100]
    steps.append({"range": edges, "color": "#334155"})
    colors = ["#F7B801", "#E85D04", "#9D0208"]
    for i, t in enumerate(thresholds):
        hi = thresholds[i + 1] if i + 1 < len(thresholds) else 100
        steps.append({"range": [t, hi], "color": colors[min(i, len(colors) - 1)]})
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=None if pd.isna(score) else float(score),
            number={"valueformat": ".1f"},
            title={"text": title},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#F7931A", "thickness": 0.25},
                "steps": steps,
            },
        )
    )
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def sell_target_gauge(ratchet: float, cap: float) -> go.Figure:
    """Cumulative sell target of the cycle (% of the base position) against the cap."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(ratchet) * 100.0,
            number={"suffix": "%", "valueformat": ".0f"},
            title={"text": "Venda acumulada-alvo no ciclo"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#E85D04"},
                "steps": [{"range": [cap * 100.0, 100], "color": "#334155"}],
                "threshold": {"line": {"color": "#F7931A", "width": 3}, "value": cap * 100.0},
            },
        )
    )
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _phase_spans(weeks: pd.DataFrame) -> List[Tuple[pd.Timestamp, pd.Timestamp, str]]:
    ph = weeks["phase"]
    block = (ph != ph.shift()).cumsum()
    spans = []
    for _, g in weeks.groupby(block):
        spans.append((g.index[0], g.index[-1] + pd.Timedelta(days=6), g["phase"].iloc[0]))
    return spans


def price_phases_chart(weeks: pd.DataFrame, events: List[Event], title: str = "Preço (escala log) e fases") -> go.Figure:
    """Weekly price on a log scale with shaded phases and the sell/cycle events marked."""
    fig = go.Figure()
    for a, b, phase in _phase_spans(weeks):
        if phase != Phase.HOLD.value:
            fig.add_vrect(x0=a, x1=b, fillcolor=PHASE_COLORS[phase], line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=weeks.index, y=weeks["price"], mode="lines", name="preço (USD)", line={"color": "#F7931A", "width": 2}))
    marks = {EventType.SELL_STEP: ("venda", "#E85D04", "triangle-down"), EventType.CYCLE_START: ("novo ciclo", "#00B4D8", "circle")}
    for etype, (label, color, symbol) in marks.items():
        xs = [pd.Timestamp(e.date) for e in events if e.type == etype]
        ys = [weeks["price"].get(x) for x in xs]
        if xs:
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=label, marker={"color": color, "symbol": symbol, "size": 10}))
    fig.update_yaxes(type="log", title="USD", gridcolor="rgba(128, 128, 128, 0.15)")
    fig.update_xaxes(gridcolor="rgba(128, 128, 128, 0.15)")
    fig.update_layout(
        title=title,
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def equity_chart(frames: Dict[str, pd.DataFrame], title: str = "Patrimônio (USD)") -> go.Figure:
    eq = frames["equity"]
    fig = go.Figure()
    for col in eq.columns:
        fig.add_trace(go.Scatter(x=eq.index, y=eq[col], mode="lines", name=col))
    fig.update_yaxes(type="log", title="USD", gridcolor="rgba(128, 128, 128, 0.15)")
    fig.update_xaxes(gridcolor="rgba(128, 128, 128, 0.15)")
    fig.update_layout(
        title=title,
        height=380,
        margin=dict(l=20, r=20, t=50, b=20),
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def score_history_chart(
    weeks: pd.DataFrame,
    arm_score: float = 25.0,
    ladder: Sequence[Tuple[float, float]] = ((85.0, 0.05), (90.0, 0.15), (93.0, 0.30)),
    title: str = "Histórico do Score de Valuation (0–100)",
) -> go.Figure:
    """Historical valuation score over time with accumulation and sell zones shaded."""
    fig = go.Figure()

    # Green accumulation band (0 to arm_score)
    fig.add_hrect(
        y0=0, y1=arm_score,
        fillcolor="rgba(0, 168, 107, 0.15)", line_width=0,
        annotation_text=f"Zona de Acúmulo (≤ {arm_score:.0f})",
        annotation_position="bottom right",
    )

    # Orange/Red ladder zones
    thresholds = [t for t, _ in ladder]
    if thresholds:
        first_t = thresholds[0]
        fig.add_hrect(
            y0=first_t, y1=100,
            fillcolor="rgba(232, 93, 4, 0.12)", line_width=0,
            annotation_text="Zona de Realização (≥ 85)",
            annotation_position="top right",
        )
        for t in thresholds:
            fig.add_hline(
                y=t, line_dash="dash", line_color="rgba(232, 93, 4, 0.6)",
                annotation_text=f"Degrau {t:.0f}", annotation_position="top left",
            )

    # Line of actual score
    score_series = weeks["score"].fillna(weeks["score_min"])
    fig.add_trace(
        go.Scatter(
            x=weeks.index,
            y=score_series,
            mode="lines",
            name="Score de Valuation",
            line=dict(color="#00B4D8", width=2),
        )
    )

    fig.update_yaxes(range=[0, 100], title="Score (0–100)", gridcolor="rgba(128, 128, 128, 0.15)")
    fig.update_xaxes(gridcolor="rgba(128, 128, 128, 0.15)")
    fig.update_layout(
        title=title,
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
