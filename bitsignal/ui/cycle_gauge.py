"""Macro cycle regime gauge and operational intensity calculator based on national execution strategy."""

from typing import Any, Dict
import pandas as pd
import plotly.graph_objects as go


def get_cycle_stage_info(
    price_usd: float,
    cycle_ath_usd: float = 126000.0,
    usd_brl_rate: float = 5.80,
    total_reserve_brl: float = 100000.0,
    total_position_btc: float = 0.5,
) -> Dict[str, Any]:
    """Calculate the active cycle stage, regime, and suggested entry/exit intensity.

    Based strictly on 'Plano de Entrada e Saída de Bitcoin — Corretoras Nacionais'.
    """
    ratio = price_usd / cycle_ath_usd if cycle_ath_usd > 0 else 1.0
    price_brl = price_usd * usd_brl_rate

    # 1. Distribution Stages (Bull Market Expansion)
    if ratio >= 2.50:
        return {
            "stage_id": "V5",
            "stage_name": "V5 — Topo Extremo / Mania Final",
            "phase": "DISTRIBUIÇÃO (SAÍDA)",
            "action": "VENDA",
            "intensity_pct": 15.0,
            "cum_intensity_pct": 75.0,
            "target_threshold_usd": 2.50 * cycle_ath_usd,
            "target_threshold_brl": 2.50 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Posição Total em BTC (15%)",
            "volume_btc": round(total_position_btc * 0.15, 8),
            "volume_brl": round(total_position_btc * 0.15 * price_brl, 2),
            "color": "#9D0208",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Desova final do ciclo. Venda de 15% da posição original (totalizando 75% vendidos). Preservar 10% de Moonbag soberana.",
            "tax_note": "Atenção ao limite de R$ 35k/mês de corretoras nacionais. Se volume exceder R$ 70k, tributação de 15% na DARF código 4600.",
        }
    elif ratio >= 2.00:
        return {
            "stage_id": "V4",
            "stage_name": "V4 — Top Warning / Euforia Macro",
            "phase": "DISTRIBUIÇÃO (SAÍDA)",
            "action": "VENDA",
            "intensity_pct": 20.0,
            "cum_intensity_pct": 60.0,
            "target_threshold_usd": 2.00 * cycle_ath_usd,
            "target_threshold_brl": 2.00 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Posição Total em BTC (20%)",
            "volume_btc": round(total_position_btc * 0.20, 8),
            "volume_brl": round(total_position_btc * 0.20 * price_brl, 2),
            "color": "#DC2F02",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "2.0x ATH atingido ou euforia on-chain. Venda de 20% da posição total (acumulado 60%). Estacionar em CDI diário.",
            "tax_note": "Avaliar split intermensal se a execução ocorrer a partir do dia 25 e o montante estiver entre R$ 35k e R$ 70k.",
        }
    elif ratio >= 1.60:
        return {
            "stage_id": "V3",
            "stage_name": "V3 — Aceleração Bullish (1.6x ATH)",
            "phase": "DISTRIBUIÇÃO (SAÍDA)",
            "action": "VENDA",
            "intensity_pct": 15.0,
            "cum_intensity_pct": 40.0,
            "target_threshold_usd": 1.60 * cycle_ath_usd,
            "target_threshold_brl": 1.60 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Posição Total em BTC (15%)",
            "volume_btc": round(total_position_btc * 0.15, 8),
            "volume_brl": round(total_position_btc * 0.15 * price_brl, 2),
            "color": "#E85D04",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Expansão forte de bull market. Venda de 15% da posição total (acumulado 40%). Ordens limitadas escalonadas com collar de 0,3%.",
            "tax_note": "Saque via PIX para conta corrente própria no mesmo dia. Cuidado com limite noturno bancário (20h-06h).",
        }
    elif ratio >= 1.30:
        return {
            "stage_id": "V2",
            "stage_name": "V2 — Expansão de Ciclo (1.3x ATH)",
            "phase": "DISTRIBUIÇÃO (SAÍDA)",
            "action": "VENDA",
            "intensity_pct": 15.0,
            "cum_intensity_pct": 25.0,
            "target_threshold_usd": 1.30 * cycle_ath_usd,
            "target_threshold_brl": 1.30 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Posição Total em BTC (15%)",
            "volume_btc": round(total_position_btc * 0.15, 8),
            "volume_brl": round(total_position_btc * 0.15 * price_brl, 2),
            "color": "#F39200",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Primeira grande extensão acima da máxima anterior. Venda de 15% da posição total (acumulado 25%).",
            "tax_note": "Permanece com stops móveis (21w EMA e 50w SMA) ativos para todo o saldo remanescente.",
        }
    elif ratio > 1.00:
        return {
            "stage_id": "V1",
            "stage_name": "V1 — Novo Recorde Histórico (> ATH)",
            "phase": "DISTRIBUIÇÃO (SAÍDA)",
            "action": "VENDA",
            "intensity_pct": 10.0,
            "cum_intensity_pct": 10.0,
            "target_threshold_usd": 1.00 * cycle_ath_usd,
            "target_threshold_brl": 1.00 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Posição Total em BTC (10%)",
            "volume_btc": round(total_position_btc * 0.10, 8),
            "volume_brl": round(total_position_btc * 0.10 * price_brl, 2),
            "color": "#F7B801",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Fechamento semanal confirma novo ATH. Desinvestimento inicial de 10% da posição total. Ativação oficial dos trailing stops.",
            "tax_note": "Venda de pequeno porte prioritariamente isenta sob o teto mensal de R$ 35k da RFB.",
        }

    # 2. Neutral Zone (Transition / Hodl)
    elif ratio > 0.70:
        return {
            "stage_id": "NEUTRO",
            "stage_name": "Zona Neutra / Transição Macro",
            "phase": "AGUARDAR / HODL",
            "action": "NENHUMA (HODL)",
            "intensity_pct": 0.0,
            "cum_intensity_pct": 0.0,
            "target_threshold_usd": 0.70 * cycle_ath_usd,
            "target_threshold_brl": 0.70 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Nenhum aporte ou venda",
            "volume_btc": 0.0,
            "volume_brl": 0.0,
            "color": "#6C757D",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Preço entre -30% e 0% da máxima histórica. Zona de transição: sem compras por degrau e sem vendas de distribuição. Manter custódia fria.",
            "tax_note": "Nenhuma alienação programada. Sem impacto fiscal.",
        }

    # 3. Accumulation Stages (Bear Market Discounts)
    elif ratio > 0.55:
        # C0 / Base DCA (-30% ATH)
        dca_monthly_brl = round(total_reserve_brl * 0.30 / 12, 2)
        dca_monthly_btc = round(dca_monthly_brl / price_brl, 8) if price_brl > 0 else 0.0
        return {
            "stage_id": "C0",
            "stage_name": "C0 — Base DCA Ativo (-30% ATH)",
            "phase": "ACUMULAÇÃO (ENTRADA)",
            "action": "COMPRA",
            "intensity_pct": 30.0,
            "cum_intensity_pct": 30.0,
            "target_threshold_usd": 0.70 * cycle_ath_usd,
            "target_threshold_brl": 0.70 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Reserva R (30% em 12 parcelas mensais)",
            "volume_btc": dca_monthly_btc,
            "volume_brl": dca_monthly_brl,
            "color": "#00B4D8",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Preço fechou 30% abaixo do ATH. Disparo do DCA contínuo: alocação de 30% da Reserva R dividida em 12 parcelas mensais de 2,5%.",
            "tax_note": "Compras em corretoras nacionais não pagam imposto, mas formam o Custo Médio Ponderado (CMP) que reduz o ganho futuro.",
        }
    elif ratio > 0.45:
        # C1 (-45% ATH)
        return {
            "stage_id": "C1",
            "stage_name": "C1 — Primeiro Degrau de Queda (-45% ATH)",
            "phase": "ACUMULAÇÃO (ENTRADA)",
            "action": "COMPRA",
            "intensity_pct": 15.0,
            "cum_intensity_pct": 45.0,
            "target_threshold_usd": 0.55 * cycle_ath_usd,
            "target_threshold_brl": 0.55 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Reserva R (15% em lote único)",
            "volume_btc": round((total_reserve_brl * 0.15) / price_brl, 8) if price_brl > 0 else 0.0,
            "volume_brl": round(total_reserve_brl * 0.15, 2),
            "color": "#00CC96",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Queda atinge -45% do ATH. Aporte imediato de 15% da Reserva R. Ordens limitadas 1% a 2% abaixo do fechamento.",
            "tax_note": "Aporte em lote único. Movimentar para autocustódia após liquidação na corretora.",
        }
    elif ratio > 0.35:
        # C2 (-55% ATH)
        return {
            "stage_id": "C2",
            "stage_name": "C2 — Desconto Severo de Ciclo (-55% ATH)",
            "phase": "ACUMULAÇÃO (ENTRADA)",
            "action": "COMPRA",
            "intensity_pct": 20.0,
            "cum_intensity_pct": 65.0,
            "target_threshold_usd": 0.45 * cycle_ath_usd,
            "target_threshold_brl": 0.45 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Reserva R (20% em lote único)",
            "volume_btc": round((total_reserve_brl * 0.20) / price_brl, 8) if price_brl > 0 else 0.0,
            "volume_brl": round(total_reserve_brl * 0.20, 2),
            "color": "#00A86B",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Desconto histórico de -55% em relação ao topo. Aporte de 20% da Reserva R (acumulado de 65% investido).",
            "tax_note": "Adicionar à planilha de controle de custo médio ponderado.",
        }
    else:
        # C3 (<= -65% ATH)
        return {
            "stage_id": "C3",
            "stage_name": "C3 — Capitulação Máxima / Fundo (-65% ATH)",
            "phase": "ACUMULAÇÃO (ENTRADA)",
            "action": "COMPRA",
            "intensity_pct": 20.0,
            "cum_intensity_pct": 85.0,
            "target_threshold_usd": 0.35 * cycle_ath_usd,
            "target_threshold_brl": 0.35 * cycle_ath_usd * usd_brl_rate,
            "allocation_base": "Reserva R (20% em lote único)",
            "volume_btc": round((total_reserve_brl * 0.20) / price_brl, 8) if price_brl > 0 else 0.0,
            "volume_brl": round(total_reserve_brl * 0.20, 2),
            "color": "#007850",
            "ratio": ratio,
            "drawdown_pct": round((ratio - 1.0) * 100, 1),
            "description": "Capitulação macro extrema (queda de -65% do ATH ou MVRV Z-Score <= 0). Aporte de 20% de R (acumulado 85%).",
            "tax_note": "Aporte máximo de capitulação. O restante (15%) aguarda confirmação de rompimento da 50w SMA (Degrau C4).",
        }


def render_cycle_regime_gauge(current_price_usd: float, cycle_ath_usd: float = 126000.0) -> go.Figure:
    """Generate the Plotly Macro Cycle Regime Gauge based on national strategy price thresholds."""
    c3_max = 0.35 * cycle_ath_usd
    c2_max = 0.45 * cycle_ath_usd
    c1_max = 0.55 * cycle_ath_usd
    c0_max = 0.70 * cycle_ath_usd
    ath_val = 1.00 * cycle_ath_usd
    v2_val = 1.30 * cycle_ath_usd
    v3_val = 1.60 * cycle_ath_usd
    v4_val = 2.00 * cycle_ath_usd
    v5_val = 2.50 * cycle_ath_usd
    gauge_max = 2.70 * cycle_ath_usd

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=current_price_usd,
            number={"prefix": "$", "valueformat": ",.0f", "font": {"size": 28}},
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": f"<b>Medidor de Ciclo — Degraus de Preço (ATH: ${cycle_ath_usd:,.0f})</b>", "font": {"size": 16}},
            gauge={
                "axis": {
                    "range": [30000, gauge_max],
                    "tickwidth": 1,
                    "tickcolor": "white",
                    "tickformat": "$,.0f",
                    "nticks": 9,
                },
                "bar": {"color": "#111111", "thickness": 0.28},
                "steps": [
                    {"range": [30000, c3_max], "color": "#007850"},   # C3 (-65%)
                    {"range": [c3_max, c2_max], "color": "#00A86B"},  # C2 (-55%)
                    {"range": [c2_max, c1_max], "color": "#00CC96"},  # C1 (-45%)
                    {"range": [c1_max, c0_max], "color": "#00B4D8"},  # C0 (-30%)
                    {"range": [c0_max, ath_val], "color": "#6C757D"}, # Neutro (HODL)
                    {"range": [ath_val, v2_val], "color": "#F7B801"}, # V1 (>ATH)
                    {"range": [v2_val, v3_val], "color": "#F39200"},  # V2 (1.3x)
                    {"range": [v3_val, v4_val], "color": "#E85D04"},  # V3 (1.6x)
                    {"range": [v4_val, v5_val], "color": "#DC2F02"},  # V4 (2.0x)
                    {"range": [v5_val, gauge_max], "color": "#9D0208"}, # V5 (2.5x)
                ],
                "threshold": {
                    "line": {"color": "white", "width": 4},
                    "thickness": 0.8,
                    "value": current_price_usd,
                },
            },
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=25, r=25, t=50, b=25),
    )
    return fig


def render_operational_intensity_gauge(stage_info: Dict[str, Any]) -> go.Figure:
    """Render a visual gauge showing the suggested operational intensity from -100% (Sell) to +100% (Buy)."""
    action = stage_info["action"]
    pct = stage_info["intensity_pct"]

    if action == "COMPRA":
        val = pct  # Positive for entry
        bar_color = "#00CC96"
        label = f"+{pct:.0f}% de R (COMPRA)"
    elif action == "VENDA":
        val = -pct  # Negative for exit
        bar_color = "#EF553B"
        label = f"-{pct:.0f}% da Posição (VENDA)"
    else:
        val = 0.0
        bar_color = "#6C757D"
        label = "0% (AGUARDAR / HODL)"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=val,
            number={"suffix": "%", "valueformat": "+.0f", "font": {"size": 28}},
            title={"text": f"<b>Intensidade Operacional Sugerida</b><br><span style='font-size:12px;color:gray'>{label}</span>", "font": {"size": 15}},
            gauge={
                "axis": {"range": [-50, 50], "tickwidth": 1, "tickformat": "+.0f"},
                "bar": {"color": bar_color, "thickness": 0.35},
                "steps": [
                    {"range": [-50, -20], "color": "rgba(220, 47, 2, 0.4)"},    # Forte Venda
                    {"range": [-20, -5], "color": "rgba(247, 184, 1, 0.3)"},    # Venda Inicial
                    {"range": [-5, 5], "color": "rgba(108, 117, 125, 0.2)"},    # Neutro
                    {"range": [5, 20], "color": "rgba(0, 204, 150, 0.3)"},     # Compra Moderada
                    {"range": [20, 50], "color": "rgba(0, 120, 80, 0.4)"},     # Compra Agressiva
                ],
                "threshold": {
                    "line": {"color": "white", "width": 4},
                    "thickness": 0.8,
                    "value": val,
                },
            },
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=25, r=25, t=50, b=25),
    )
    return fig


def get_all_stages_table(
    cycle_ath_usd: float = 126000.0,
    usd_brl_rate: float = 5.80,
    current_price_usd: float = 95000.0,
    total_reserve_brl: float = 100000.0,
    total_position_btc: float = 0.5,
) -> pd.DataFrame:
    """Generate a comprehensive overview of all accumulation and distribution stages."""
    stages = [
        # Accumulation
        {
            "Fase": "Acumulação (Entrada)",
            "Degrau": "C3",
            "Gatilho": "-65% do ATH ou MVRV <= 0",
            "Preço USD": f"≤ ${0.35 * cycle_ath_usd:,.0f}",
            "Preço BRL": f"≤ R$ {0.35 * cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "20% de R",
            "Volume Estimado": f"R$ {total_reserve_brl * 0.20:,.2f}",
            "Status": "🟢 ATIVO" if current_price_usd <= 0.35 * cycle_ath_usd else "⏳ Aguardando",
        },
        {
            "Fase": "Acumulação (Entrada)",
            "Degrau": "C2",
            "Gatilho": "-55% do ATH",
            "Preço USD": f"≤ ${0.45 * cycle_ath_usd:,.0f}",
            "Preço BRL": f"≤ R$ {0.45 * cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "20% de R",
            "Volume Estimado": f"R$ {total_reserve_brl * 0.20:,.2f}",
            "Status": "🟢 ATIVO" if current_price_usd <= 0.45 * cycle_ath_usd and current_price_usd > 0.35 * cycle_ath_usd else ("✅ Superado" if current_price_usd <= 0.35 * cycle_ath_usd else "⏳ Aguardando"),
        },
        {
            "Fase": "Acumulação (Entrada)",
            "Degrau": "C1",
            "Gatilho": "-45% do ATH",
            "Preço USD": f"≤ ${0.55 * cycle_ath_usd:,.0f}",
            "Preço BRL": f"≤ R$ {0.55 * cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "15% de R",
            "Volume Estimado": f"R$ {total_reserve_brl * 0.15:,.2f}",
            "Status": "🟢 ATIVO" if current_price_usd <= 0.55 * cycle_ath_usd and current_price_usd > 0.45 * cycle_ath_usd else ("✅ Superado" if current_price_usd <= 0.45 * cycle_ath_usd else "⏳ Aguardando"),
        },
        {
            "Fase": "Acumulação (Entrada)",
            "Degrau": "C0 (DCA)",
            "Gatilho": "-30% do ATH",
            "Preço USD": f"≤ ${0.70 * cycle_ath_usd:,.0f}",
            "Preço BRL": f"≤ R$ {0.70 * cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "30% de R (12x)",
            "Volume Estimado": f"12x R$ {total_reserve_brl * 0.30 / 12:,.2f}",
            "Status": "🔵 ATIVO" if current_price_usd <= 0.70 * cycle_ath_usd and current_price_usd > 0.55 * cycle_ath_usd else ("✅ Superado" if current_price_usd <= 0.55 * cycle_ath_usd else "⏳ Aguardando"),
        },
        # Neutral
        {
            "Fase": "Zona Neutra",
            "Degrau": "HODL",
            "Gatilho": "-30% a 0% do ATH",
            "Preço USD": f"${0.70 * cycle_ath_usd:,.0f} a ${cycle_ath_usd:,.0f}",
            "Preço BRL": f"R$ {0.70 * cycle_ath_usd * usd_brl_rate:,.0f} a R$ {cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "0%",
            "Volume Estimado": "Nenhum (HODL)",
            "Status": "🟣 ATIVO" if 0.70 * cycle_ath_usd < current_price_usd <= cycle_ath_usd else "—",
        },
        # Distribution
        {
            "Fase": "Distribuição (Saída)",
            "Degrau": "V1",
            "Gatilho": "Novo ATH (> 1.0x ATH)",
            "Preço USD": f"> ${cycle_ath_usd:,.0f}",
            "Preço BRL": f"> R$ {cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "10% da Posição",
            "Volume Estimado": f"{total_position_btc * 0.10:.4f} BTC",
            "Status": "🟡 ATIVO" if current_price_usd > cycle_ath_usd and current_price_usd < 1.30 * cycle_ath_usd else ("✅ Executado" if current_price_usd >= 1.30 * cycle_ath_usd else "⏳ Aguardando"),
        },
        {
            "Fase": "Distribuição (Saída)",
            "Degrau": "V2",
            "Gatilho": "1.3x ATH",
            "Preço USD": f"≥ ${1.30 * cycle_ath_usd:,.0f}",
            "Preço BRL": f"≥ R$ {1.30 * cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "15% da Posição",
            "Volume Estimado": f"{total_position_btc * 0.15:.4f} BTC",
            "Status": "🟠 ATIVO" if current_price_usd >= 1.30 * cycle_ath_usd and current_price_usd < 1.60 * cycle_ath_usd else ("✅ Executado" if current_price_usd >= 1.60 * cycle_ath_usd else "⏳ Aguardando"),
        },
        {
            "Fase": "Distribuição (Saída)",
            "Degrau": "V3",
            "Gatilho": "1.6x ATH",
            "Preço USD": f"≥ ${1.60 * cycle_ath_usd:,.0f}",
            "Preço BRL": f"≥ R$ {1.60 * cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "15% da Posição",
            "Volume Estimado": f"{total_position_btc * 0.15:.4f} BTC",
            "Status": "🟠 ATIVO" if current_price_usd >= 1.60 * cycle_ath_usd and current_price_usd < 2.00 * cycle_ath_usd else ("✅ Executado" if current_price_usd >= 2.00 * cycle_ath_usd else "⏳ Aguardando"),
        },
        {
            "Fase": "Distribuição (Saída)",
            "Degrau": "V4",
            "Gatilho": "2.0x ATH ou Euforia",
            "Preço USD": f"≥ ${2.00 * cycle_ath_usd:,.0f}",
            "Preço BRL": f"≥ R$ {2.00 * cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "20% da Posição",
            "Volume Estimado": f"{total_position_btc * 0.20:.4f} BTC",
            "Status": "🔴 ATIVO" if current_price_usd >= 2.00 * cycle_ath_usd and current_price_usd < 2.50 * cycle_ath_usd else ("✅ Executado" if current_price_usd >= 2.50 * cycle_ath_usd else "⏳ Aguardando"),
        },
        {
            "Fase": "Distribuição (Saída)",
            "Degrau": "V5",
            "Gatilho": "2.5x ATH",
            "Preço USD": f"≥ ${2.50 * cycle_ath_usd:,.0f}",
            "Preço BRL": f"≥ R$ {2.50 * cycle_ath_usd * usd_brl_rate:,.0f}",
            "Intensidade": "15% da Posição",
            "Volume Estimado": f"{total_position_btc * 0.15:.4f} BTC",
            "Status": "🔴 ATIVO" if current_price_usd >= 2.50 * cycle_ath_usd else "⏳ Aguardando",
        },
        {
            "Fase": "Custódia Perpétua",
            "Degrau": "Moonbag",
            "Gatilho": "Reserva Soberana",
            "Preço USD": "Nunca vendido",
            "Preço BRL": "Nunca vendido",
            "Intensidade": "10% da Posição",
            "Volume Estimado": f"{total_position_btc * 0.10:.4f} BTC",
            "Status": "🔒 Intocável",
        },
    ]
    return pd.DataFrame(stages)
