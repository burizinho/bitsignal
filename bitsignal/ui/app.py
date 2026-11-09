"""Interactive local Streamlit dashboard for BitSignal."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys

# Ensure repository root is in sys.path BEFORE any bitsignal imports (needed for Streamlit Cloud deployment)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
root_str = str(ROOT_DIR)
while root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# Purge any stale bitsignal modules cached from site-packages (Streamlit Cloud container persistence)
for mod_name in list(sys.modules.keys()):
    if mod_name == "bitsignal" or mod_name.startswith("bitsignal."):
        mod_obj = sys.modules.get(mod_name)
        mod_file = getattr(mod_obj, "__file__", None)
        if mod_file and not mod_file.startswith(root_str):
            del sys.modules[mod_name]

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from bitsignal.storage.db import (  # noqa: E402
    get_executed_stages,
    get_portfolio_summary,
    get_portfolio_transactions,
    record_portfolio_transaction,
)
from bitsignal.strategy.models import PortfolioTransaction, StageType, TransactionType  # noqa: E402
from bitsignal.strategy.tax_br import compute_darf_for_month, get_monthly_accumulated_alienation  # noqa: E402
from bitsignal.ui.cycle_gauge import (  # noqa: E402
    get_all_stages_table,
    get_cycle_stage_info,
    render_cycle_regime_gauge,
    render_operational_intensity_gauge,
)

DEFAULT_DB_PATH = str(ROOT_DIR / "data" / "bitsignal.db")
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)


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


OLD_PANEL_WARNING = "Em revisão: as ordens desta tela vêm do modelo antigo e não devem ser seguidas."


def main():
    """Renderiza o painel. Chamado a cada execução do Streamlit (inclusive nos reruns)."""
    st.set_page_config(
        page_title="BitSignal - Bitcoin Macro Cycle Sentinel",
        page_icon="⚡",
        layout="wide",
    )
    st.warning(OLD_PANEL_WARNING)

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

    tab_macro, tab_plan_gauge, tab_strategy = st.tabs(["🌐 Sentinela Macro Global", "🎯 Termômetro de Ciclo (Plano Nacional)", "🇧🇷 Carteira & Execução Fiscal"])

    with tab_macro:
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

    with tab_plan_gauge:
        st.header("🎯 Termômetro de Ciclo — Degraus de Entrada e Saída Nacional")
        st.caption("Estratégia baseada em preço relativo à máxima do ciclo (ATH = US$ 126 mil) com gestão de intensidade percentual e regras fiscais brasileiras.")

        # Configuration Expander
        with st.expander("⚙️ Parâmetros do Ciclo & Carteira", expanded=False):
            p_col1, p_col2, p_col3, p_col4 = st.columns(4)
            cfg_ath_usd = p_col1.number_input("Máxima de Referência (ATH US$)", value=126000.0, step=1000.0, format="%.2f")
            cfg_reserve_brl = p_col2.number_input("Reserva Total de Compra (R$)", value=100000.0, step=5000.0, format="%.2f")
            cfg_pos_btc = p_col3.number_input("Posição Base de Saída (BTC)", value=0.50, step=0.05, format="%.4f")
            cfg_usd_brl = p_col4.number_input("Câmbio USD/BRL Estimado", value=5.80, step=0.05, format="%.2f")

        spot_usd = btc_price if btc_price > 0 else 95000.0
        spot_brl = spot_usd * cfg_usd_brl
        stage_info = get_cycle_stage_info(
            price_usd=spot_usd,
            cycle_ath_usd=cfg_ath_usd,
            usd_brl_rate=cfg_usd_brl,
            total_reserve_brl=cfg_reserve_brl,
            total_position_btc=cfg_pos_btc,
        )

        # Top KPI summary cards
        k_col1, k_col2, k_col3, k_col4 = st.columns(4)
        k_col1.metric("Preço BTC (Spot USD)", f"${spot_usd:,.2f}", f"R$ {spot_brl:,.2f}")
        mult_str = f"{stage_info['ratio']:.2f}x"
        drawdown_str = f"{stage_info['drawdown_pct']:+.1f}%"
        k_col2.metric("Múltiplo sobre o Topo (ATH)", mult_str, drawdown_str)
        k_col3.metric("Fase do Ciclo", stage_info["phase"])
        k_col4.metric("Degrau Vigente", stage_info["stage_id"])

        st.markdown("---")

        # Gauges: Regime on Left, Intensity on Right
        g_left, g_right = st.columns([1.2, 1])

        with g_left:
            fig_regime = render_cycle_regime_gauge(current_price_usd=spot_usd, cycle_ath_usd=cfg_ath_usd)
            st.plotly_chart(fig_regime, use_container_width=True)

        with g_right:
            fig_intensity = render_operational_intensity_gauge(stage_info)
            st.plotly_chart(fig_intensity, use_container_width=True)

        # Actionable Operational Callout Box
        if stage_info["action"] == "COMPRA":
            st.success(
                f"### 🟢 RECOMENDAÇÃO OPERACIONAL: {stage_info['stage_name']}\n\n"
                f"• **Intensidade Sugerida:** `{stage_info['intensity_pct']:.0f}%` ({stage_info['allocation_base']})\n"
                f"• **Volume a Aportar:** `R$ {stage_info['volume_brl']:,.2f}` (~ `{stage_info['volume_btc']:.8f} BTC`)\n"
                f"• **Orientação de Execução:** {stage_info['description']}\n"
                f"• **Engenharia Fiscal:** {stage_info['tax_note']}"
            )
        elif stage_info["action"] == "VENDA":
            st.warning(
                f"### 🔴 RECOMENDAÇÃO OPERACIONAL: {stage_info['stage_name']}\n\n"
                f"• **Intensidade Sugerida:** `{stage_info['intensity_pct']:.0f}%` ({stage_info['allocation_base']})\n"
                f"• **Desinvestimento:** `{stage_info['volume_btc']:.8f} BTC` (~ `R$ {stage_info['volume_brl']:,.2f}`)\n"
                f"• **Orientação de Execução:** {stage_info['description']}\n"
                f"• **Engenharia Fiscal:** {stage_info['tax_note']}"
            )
        else:
            st.info(
                f"### 🟣 SITUAÇÃO ATUAL: {stage_info['stage_name']}\n\n"
                f"• **Intensidade Sugerida:** `0%` (Sem compras adicionais e sem desinvestimento)\n"
                f"• **Orientação:** {stage_info['description']}\n"
                f"• **Estratégia:** Aguardar fechamento semanal dominical (21h BRT). Os stops móveis protegem contra reversões."
            )

        st.markdown("---")

        # Interactive Scenario Simulator
        st.subheader("🧪 Simulador Interativo de Cenários de Preço")
        st.caption("Arraste o controle para simular como a estratégia se comporta em diferentes patamares de cotação.")

        sim_price = st.slider(
            "Cotação Simulada do Bitcoin (US$):",
            min_value=30000.0,
            max_value=350000.0,
            value=float(spot_usd),
            step=1000.0,
            format="$%.0f",
        )

        sim_info = get_cycle_stage_info(
            price_usd=sim_price,
            cycle_ath_usd=cfg_ath_usd,
            usd_brl_rate=cfg_usd_brl,
            total_reserve_brl=cfg_reserve_brl,
            total_position_btc=cfg_pos_btc,
        )

        sim_col1, sim_col2, sim_col3 = st.columns(3)
        sim_col1.metric("Degrau no Cenário", sim_info["stage_name"])
        sim_col2.metric("Intensidade da Operação", f"{sim_info['intensity_pct']:.0f}% ({sim_info['action']})")
        vol_text = f"R$ {sim_info['volume_brl']:,.2f}" if sim_info["action"] == "COMPRA" else f"{sim_info['volume_btc']:.4f} BTC (R$ {sim_info['volume_brl']:,.2f})"
        sim_col3.metric("Volume Sugerido", vol_text if sim_info["action"] != "NENHUMA (HODL)" else "0")

        st.markdown("---")

        # Full Stages Table
        st.subheader("📋 Tabela Estratégica Completa — Faixas, Degraus e Intensidades")
        df_all_stages = get_all_stages_table(
            cycle_ath_usd=cfg_ath_usd,
            usd_brl_rate=cfg_usd_brl,
            current_price_usd=spot_usd,
            total_reserve_brl=cfg_reserve_brl,
            total_position_btc=cfg_pos_btc,
        )
        st.dataframe(df_all_stages, use_container_width=True)

        # Trailing stops rules box
        st.markdown("---")
        st.subheader("🛡️ Trailing Stops Dominicais (Proteção Dinâmica de Saída)")
        ts_col1, ts_col2 = st.columns(2)
        with ts_col1:
            st.markdown(
                "**Stop 1 (Fechamento Semanal < 21w EMA):**\n\n"
                "• **Gatilho:** Fechamento dominical às 21h00 BRT abaixo da Média Móvel Exponencial de 21 semanas.\n"
                "• **Intensidade:** Venda imediata de **50% do saldo restante**.\n"
                "• **Objetivo:** Proteger ganhos antes da confirmação de bear market prolongado."
            )
        with ts_col2:
            st.markdown(
                "**Stop 2 (Fechamento Semanal < 50w SMA):**\n\n"
                "• **Gatilho:** Fechamento dominical às 21h00 BRT abaixo da Média Móvel Simples de 50 semanas.\n"
                "• **Intensidade:** Venda imediata de **100% do saldo restante** (exceto os 10% de Moonbag).\n"
                "• **Objetivo:** Encerrar a fase de saída do ciclo e migrar liquidez para renda fixa (CDI) até a próxima fase de entrada."
            )


    with tab_strategy:
        st.header("🇧🇷 Estratégia de Execução Nacional & Engenharia Fiscal")
        st.caption("Controle patrimonial, Custo Médio Ponderado (CMP) e conformidade tributária RFB (Lei 8.981/95 e IN 1.888).")

        summary = get_portfolio_summary(DB_PATH)
        executed_stages = set(get_executed_stages(DB_PATH))
        now_str = datetime.now(timezone.utc).strftime("%Y-%m")
        monthly_alienation = get_monthly_accumulated_alienation(month_year=now_str, db_path=DB_PATH)
        tax_report = compute_darf_for_month(month_year=now_str, db_path=DB_PATH)

        # Metric KPI Cards
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        s_col1.metric("Saldo em Custódia", f"{summary.current_btc_balance:.8f} BTC")
        s_col2.metric("Custo Médio Ponderado", f"R$ {summary.current_cmp_brl:,.2f}")
        s_col3.metric("Total Aportado", f"R$ {summary.total_invested_brl:,.2f}")
        s_col4.metric("Total Retirado", f"R$ {summary.total_withdrawn_brl:,.2f}")

        st.markdown("---")

        # Fiscal Gauge & DARF Status
        fg_col1, fg_col2 = st.columns([1, 1])

        with fg_col1:
            st.subheader("Termômetro de Isenção Mensal (R$ 35.000 / mês)")
            is_exempt = monthly_alienation <= 35000.0
            gauge_color = "#00CC96" if is_exempt else "#EF553B"
            fig_tax_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=monthly_alienation,
                    number={"prefix": "R$ ", "valueformat": ",.2f"},
                    gauge={
                        "axis": {"range": [0, 50000], "tickwidth": 1},
                        "bar": {"color": gauge_color, "thickness": 0.3},
                        "steps": [
                            {"range": [0, 35000], "color": "rgba(0, 204, 150, 0.2)"},
                            {"range": [35000, 50000], "color": "rgba(239, 85, 59, 0.2)"},
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 3},
                            "thickness": 0.8,
                            "value": 35000.0,
                        },
                    },
                )
            )
            fig_tax_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_tax_gauge, use_container_width=True)

        with fg_col2:
            st.subheader(f"Apuração Fiscal RFB — {now_str}")
            if is_exempt:
                st.success(f"✅ **100% ISENTO DE IRPF** (Art. 35 da Lei 8.981/95)\n\n"
                           f"• Alienação acumulada: `R$ {monthly_alienation:,.2f}`\n"
                           f"• Margem isenta restante este mês: `R$ {max(0.0, 35000.0 - monthly_alienation):,.2f}`\n"
                           f"• Imposto a recolher: **R$ 0,00**")
            else:
                st.error(f"⚠️ **TETO DE ISENÇÃO EXCEDIDO** (Tributação a 15% via GCAP/DARF)\n\n"
                         f"• Alienação total: `R$ {monthly_alienation:,.2f}`\n"
                         f"• Ganho de Capital Líquido: `R$ {tax_report['total_gain_brl']:,.2f}`\n"
                         f"• Imposto Devido (DARF Cód 4600): **R$ {tax_report['darf_due_brl']:,.2f}**\n"
                         f"• Vencimento: Último dia útil do mês seguinte no SicalcWeb.")

        st.markdown("---")

        # Staged Cycle Progression
        st.subheader("Mapa de Degraus Estratégicos do Ciclo")
        st_col1, st_col2 = st.columns(2)

        with st_col1:
            st.markdown("**Fase de Acumulação (Bear Market):**")
            acc_stages = [
                ("C0", "DCA Inicial (-30% do ATH)", "30%"),
                ("C1", "Aporte Queda (-45% do ATH)", "15%"),
                ("C2", "Aporte Queda (-55% do ATH)", "20%"),
                ("C3", "Capitulação (-65% do ATH ou MVRV <= 0)", "20%"),
                ("C4", "Confirmação Rompimento 50w SMA", "15% + Sobras"),
            ]
            for code, label, alloc in acc_stages:
                done = code in executed_stages
                status_icon = "✅ **Executado**" if done else "⏳ Pendente"
                st.markdown(f"• `{code}`: {label} ({alloc}) — {status_icon}")

        with st_col2:
            st.markdown("**Fase de Distribuição (Bull Market & Stops):**")
            dist_stages = [
                ("V1", "Novo Topo Histórico (> ATH)", "10%"),
                ("V2", "Expansão de Ciclo (1.3x ATH)", "15%"),
                ("V3", "Expansão de Ciclo (1.6x ATH)", "15%"),
                ("V4", "Top Warning (2.0x ATH ou Euforia)", "20%"),
                ("V5", "Maximum Euphoria (2.5x ATH)", "20%"),
                ("STOP_1", "Trailing Stop 1 (Perda 21w EMA)", "50% do Saldo"),
                ("STOP_2", "Trailing Stop 2 (Perda 50w SMA)", "100% exceto Moonbag"),
            ]
            for code, label, alloc in dist_stages:
                done = code in executed_stages
                status_icon = "✅ **Executado**" if done else "⏳ Pendente"
                st.markdown(f"• `{code}`: {label} ({alloc}) — {status_icon}")

        st.markdown("---")

        # Transaction Registration & History
        st.subheader("Registro e Auditoria de Transações")

        with st.expander("➕ Registrar Nova Operação (Compra ou Venda)"):
            with st.form("tx_form", clear_on_submit=True):
                f_col1, f_col2, f_col3 = st.columns(3)
                tx_type = f_col1.selectbox("Tipo de Operação", ["BUY", "SELL"])
                stage = f_col2.selectbox("Degrau / Gatilho", [
                    "C0", "C1", "C2", "C3", "C4",
                    "V1", "V2", "V3", "V4", "V5",
                    "STOP_1", "STOP_2", "SPLIT_PART_2", "MANUAL"
                ])
                exchange = f_col3.text_input("Corretora Nacional", value="Bipa")

                f_col4, f_col5, f_col6 = st.columns(3)
                btc_amount = f_col4.number_input("Quantidade (BTC)", min_value=0.00000001, max_value=10.0, step=0.005, format="%.8f")
                price_brl = f_col5.number_input("Preço de Execução (R$/BTC)", min_value=1000.0, step=1000.0, format="%.2f")
                fee_brl = f_col6.number_input("Taxas Totais (R$)", min_value=0.0, step=1.0, format="%.2f")

                notes = st.text_input("Observações / Runbook", value="")
                submitted = st.form_submit_button("Gravar Transação no Ledger")

                if submitted:
                    try:
                        new_tx = PortfolioTransaction(
                            date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            tx_type=TransactionType(tx_type),
                            stage=StageType(stage) if stage in StageType.__members__ else StageType.C0,
                            amount_btc=btc_amount,
                            price_brl=price_brl,
                            price_usd=round(price_brl / 5.80, 2),
                            fee_brl=fee_brl,
                            exchange=exchange,
                            notes=notes,
                        )
                        record_portfolio_transaction(new_tx, db_path=DB_PATH)
                        st.success("Transação registrada com sucesso! Novo saldo recalculado.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao registrar transação: {exc}")

        # Ledger History
        txs = get_portfolio_transactions(DB_PATH, limit=100)
        if txs:
            tx_data = [
                {
                    "Data": t.date,
                    "Tipo": t.tx_type.value,
                    "Degrau": t.stage.value if hasattr(t.stage, "value") else str(t.stage),
                    "Qtd (BTC)": f"{t.amount_btc:.8f}",
                    "Preço (R$)": f"R$ {t.price_brl:,.2f}",
                    "Total (R$)": f"R$ {t.amount_btc * t.price_brl:,.2f}",
                    "Taxa (R$)": f"R$ {t.fee_brl:,.2f}",
                    "Exchange": t.exchange,
                    "Notas": t.notes or "",
                }
                for t in txs
            ]
            st.dataframe(pd.DataFrame(tx_data), use_container_width=True)
        else:
            st.info("Nenhuma transação registrada ainda no ledger da carteira.")
