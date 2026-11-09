"""BitSignal read-only dashboard (design §8, plan item 37).

Shows the model verdict for the latest closed week, in percentages only. It never executes
orders, never stores anything on disk and never shows recommendations built from stale data.
"""

import os
from pathlib import Path
import sys

# Ensure repository root is in sys.path BEFORE any bitsignal imports (needed for Streamlit Cloud deployment)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
root_str = str(ROOT_DIR)
while root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

# Drop cached bitsignal modules that are stale: loaded from outside this checkout, or whose source
# changed on disk after the import (Streamlit Cloud keeps modules in memory across a redeploy).
_loaded_at = getattr(sys.modules.get("bitsignal"), "_LOADED_AT", None)
_names = [m for m in list(sys.modules) if m == "bitsignal" or m.startswith("bitsignal.")]
_files = {m: getattr(sys.modules.get(m), "__file__", None) for m in _names}
# A loaded package without _LOADED_AT predates this check, so it is stale too.
_changed = bool(_names) and (_loaded_at is None or any(
    f and f.startswith(root_str) and os.path.exists(f) and os.path.getmtime(f) > _loaded_at for f in _files.values()
))
for mod_name, mod_file in _files.items():
    if _changed or (mod_file and not mod_file.startswith(root_str)):
        sys.modules.pop(mod_name, None)

from datetime import datetime, timezone  # noqa: E402
import time  # noqa: E402

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from bitsignal.backtest.engine import run_backtest  # noqa: E402
from bitsignal.backtest.report import HEADER as BACKTEST_HEADER, to_frames  # noqa: E402
from bitsignal.config import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    ConfigError,
    INPUT_KEYS,
    load_config,
    load_frozen_params,
    model_hash,
    validate_for_panel,
)
from bitsignal.data import dune as dune_mod  # noqa: E402
from bitsignal.data import spot as spot_mod  # noqa: E402
from bitsignal.data.coinmetrics import DataUnavailable, fetch_coinmetrics  # noqa: E402
from bitsignal.data.history import derive_daily, from_frame, load_frozen_history  # noqa: E402
from bitsignal.engine.cycle import data_status, latest_verdict  # noqa: E402
from bitsignal.engine.pipeline import run_model  # noqa: E402
from bitsignal.models import DataStatus, InputState, Phase, ScoreStatus  # noqa: E402
from bitsignal.ui import calculator, charts  # noqa: E402

# --------------------------------------------------------------------------------------
# Injection points (module level; patched by tests/test_app_smoke.py)
# --------------------------------------------------------------------------------------

CONFIG_PATH = DEFAULT_CONFIG_PATH
_BOOT = load_config(CONFIG_PATH)

INPUT_LABELS = {
    "mvrv_z": "MVRV Z",
    "price_to_sma200w": "Preço / SMA200w",
    "puell": "Puell",
    "picycle": "Pi Cycle",
    "rsi14w": "RSI(14) semanal",
    "hash_ribbon": "Hash Ribbon",
}
INPUT_VALUE_COL = {"picycle": "picycle_spread"}

ACCUMULATE_NOTICE = (
    "As compras desta fase não alteram a posição-base do ciclo atual. "
    "A meta de venda não é uma ordem automática nem considera operações já executadas."
)
RECONSTRUCTION_NOTICE = "Dados históricos recuperados ou revisados podem alterar esta reconstrução, inclusive para baixo."


def get_config():
    return load_config(CONFIG_PATH)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@st.cache_data(ttl=_BOOT.ui.cache_ttl_coinmetrics, show_spinner="Buscando o histórico da CoinMetrics…")
def load_history():
    return from_frame(fetch_coinmetrics(), source="coinmetrics_live", fetched_at=now_utc())


@st.cache_data(ttl=_BOOT.ui.cache_ttl_coinmetrics, show_spinner=False)
def cached_model(key: str, _history, _cfg):
    return run_model(_history, _cfg)


@st.cache_data(ttl=_BOOT.ui.cache_ttl_spot, show_spinner=False)
def cached_spot():
    return spot_mod.fetch_spot_usd()


@st.cache_data(show_spinner="Calculando o backtest…")
def cached_backtest(key: str, window: str, _cfg, _frozen):
    history = load_frozen_history(_cfg.data.csv_path)
    return run_backtest(history, _cfg, window=window, frozen=_frozen, sensitivities=False)


# --------------------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------------------


def _pct(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{x * 100:.0f}%"


def _d(x) -> str:
    return pd.Timestamp(x).strftime("%d/%m/%Y")


def top_line(verdict, cfg) -> str:
    if verdict.buy_all_cash:
        buy = "**todo o caixa disponível** (inclui o produto das vendas)"
    else:
        buy = f"**{_pct(verdict.buy_pct) if verdict.buy_pct is not None else '—'}** da reserva-base"
    return (
        f"Semana fechada em {_d(verdict.week)} · **{verdict.phase.label}** · "
        f"Venda acumulada-alvo no ciclo: **{_pct(verdict.sell_target)}** da posição-base "
        f"(ciclo iniciado em {_d(verdict.cycle_start_date)}) · "
        f"Compra programada nesta semana: {buy} · Motivo: {verdict.reason}"
    )


def model_label(cfg) -> str:
    return "modelo v2 (reinvestimento do caixa)" if cfg.buys.on_reset == "all_cash" else "modelo v1"


def render_spot():
    spot = cached_spot()
    if spot is None:
        st.caption("Preço agora (yfinance, somente exibição): indisponível.")
    else:
        price, ts = spot
        st.caption(f"Preço agora (yfinance, somente exibição): US$ {price:,.0f} às {ts:%H:%M} UTC")


def render_calculator(verdict, week_close: float):
    """Percentages -> amounts from numbers typed by the user. Session only: nothing is stored."""
    spot = cached_spot()
    price, source = (spot[0], "preço agora (yfinance)") if spot else (week_close, "fechamento da semana")
    with st.expander("Calculadora: converter os percentuais em valores (opcional)"):
        st.caption("Os números digitados ficam só nesta sessão do navegador: não são gravados nem viram "
                   f"registro de operações. Valores brutos, sem custos. Preço usado: {source}, US$ {price:,.0f}.")
        c1, c2 = st.columns(2)
        base = c1.number_input("BTC no início do ciclo (posição-base)", min_value=0.0, value=0.0,
                               step=0.01, format="%.8f", key="calc_base_btc")
        sold = c1.number_input("BTC já vendidos neste ciclo", min_value=0.0, value=0.0,
                               step=0.01, format="%.8f", key="calc_sold_btc")
        reserve = c2.number_input("Reserva-base (USD)", min_value=0.0, value=0.0, step=100.0,
                                  format="%.2f", key="calc_reserve_usd")
        cash = c2.number_input("Caixa disponível agora (USD)", min_value=0.0, value=0.0, step=100.0,
                               format="%.2f", key="calc_cash_usd")
        a = calculator.compute(verdict, price, base, sold, reserve, cash)
        lines = []
        if a.sell_target_btc is not None:
            lines.append(f"Venda acumulada-alvo do ciclo: **{a.sell_target_btc:.8f} BTC** "
                         f"({_pct(verdict.sell_target)} de {base:.8f} BTC). Falta vender: **{a.to_sell_btc:.8f} BTC** "
                         f"(≈ US$ {a.to_sell_usd:,.0f}).")
        if verdict.buy_all_cash:
            lines.append(f"Compra desta semana: **todo o caixa**, US$ {a.buy_usd:,.2f} ≈ **{a.buy_btc:.8f} BTC**."
                         if a.buy_usd else "Compra desta semana: todo o caixa disponível (informe o caixa).")
        elif a.buy_usd is not None:
            limit = " (limitada ao caixa informado)" if a.buy_limited_by_cash else ""
            lines.append(f"Compra desta semana: **US$ {a.buy_usd:,.2f}** ≈ **{a.buy_btc:.8f} BTC**{limit}.")
        elif not verdict.buy_pct:
            lines.append("Sem compra programada nesta semana.")
        st.markdown("\n\n".join(lines) if lines else "Informe os valores acima para ver as quantidades.")


def render_unavailable(cfg, reason: str, context_history=None):
    """Screen without verdict (Q6): no phase, no sell target, no buy."""
    last_try = st.session_state.get("last_attempt")
    when = f" (última tentativa {last_try:%d/%m %H:%M} UTC)" if last_try else ""
    st.error(f"{reason}{when}. Sem veredito nesta carga.")
    render_spot()
    cooldown = cfg.ui.retry_cooldown_s
    last_retry = st.session_state.get("last_retry_ts", 0.0)
    if st.button("Tentar de novo"):
        if time.time() - last_retry >= cooldown:
            st.session_state["last_retry_ts"] = time.time()
            load_history.clear()
            st.rerun()
        else:
            st.warning(f"Aguarde {cooldown} s entre tentativas.")
    if context_history is not None:
        st.info(
            f"Histórico em memória só para consulta — último dado {_d(context_history.as_of)}, desatualizado. "
            "Nenhuma fase, meta de venda ou compra é calculada a partir dele."
        )
        st.line_chart(context_history.daily["price"].dropna().iloc[-730:], height=260)


def render_inputs(result, history, cfg):
    last = result.weeks.iloc[-1]
    rows = []
    for name in INPUT_KEYS:
        col = INPUT_VALUE_COL.get(name, name)
        state = InputState(last[f"state_{name}"])
        value = last[col]
        rows.append(
            {
                "insumo": INPUT_LABELS[name],
                "valor": value if isinstance(value, str) else ("—" if pd.isna(value) else f"{float(value):.3f}"),
                "estado": state.label,
                "fonte": f"CoinMetrics ({'CSV congelado' if history.source == 'coinmetrics_frozen' else 'ao vivo'})",
                "data": _d(result.weeks.index[-1]),
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def render_detector(result):
    last = result.weeks.iloc[-1]
    level = int(last["level"])
    if level > 0:
        st.write(f"Detector de reversão: **episódio em N{level}**")
    elif bool(last["armed"]):
        st.write("Detector de reversão: **armado** (ATH nas últimas 52 semanas), sem episódio")
    else:
        st.write("Detector de reversão: **desarmado**")


def render_cycle(result, verdict, cfg):
    cycle_start = pd.Timestamp(verdict.cycle_start_date)
    weeks = result.weeks.loc[cycle_start:]
    st.plotly_chart(charts.price_phases_chart(result.weeks.iloc[-260:], result.events), width="stretch")
    st.caption(f"Recalculado em {now_utc():%d/%m/%Y %H:%M} UTC. {RECONSTRUCTION_NOTICE}")
    ev = [e for e in result.events if pd.Timestamp(e.date) >= cycle_start]
    if ev:
        st.dataframe(
            pd.DataFrame(
                [
                    {"data": _d(e.date), "evento": e.type.value, "mecanismo": e.mechanism,
                     "limiar": e.threshold, "antes": e.before, "depois": e.after, "nota": e.note}
                    for e in ev
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    st.caption(f"Semanas no ciclo atual: {len(weeks)}.")


def render_dune(history, cfg):
    key, qid = os.getenv("DUNE_API_KEY"), os.getenv("DUNE_QUERY_ID")
    if not key or not qid:
        return
    row = dune_mod.fetch_dune_latest(key, qid)
    if row is None:
        st.caption("Conferência Dune: indisponível.")
        return
    divs = dune_mod.compare_with(derive_daily(history, get_config()), row)
    if divs:
        st.warning("Conferência Dune: divergências — " + "; ".join(f"{d.metric} {d.delta:+.2f} em {_d(d.date)}" for d in divs))
    else:
        st.caption(f"Conferência Dune ({_d(row['date'])}): sem divergência acima dos limites.")


def render_backtest(cfg):
    frozen = load_frozen_params(cfg.backtest.frozen_params)
    current = model_hash(cfg)
    window = "calibration"
    if frozen is None or frozen.model_hash != current:
        msg = "sem parâmetros congelados" if frozen is None else "parâmetros diferentes dos congelados"
        st.warning(f"{msg.capitalize()}: status aprovado não se aplica. Mostrando só a janela de calibração.")
    elif frozen.approval is None:  # v2: no evaluation on seen data; approval only from forward data
        st.warning("Experimental: este modelo não tem avaliação gravada. A aprovação só vem da avaliação "
                   "com dados futuros (Fase 3). Mostrando só a janela de calibração.")
    else:
        window = "development"
        a = frozen.approval
        if all(a.passed.model_dump().values()):
            st.success("Desempenho histórico aprovado (critérios da Q1, gravados no congelamento). Sem promessa de rentabilidade.")
        else:
            st.warning("Experimental: os critérios financeiros da Q1 não foram todos atingidos na avaliação gravada.")
        st.dataframe(
            pd.DataFrame({"valor gravado": a.values.model_dump(), "aprovado": a.passed.model_dump()}),
            width="stretch",
        )
    rep = cached_backtest(current, window, cfg, frozen if window == "development" else None)
    if window == "development":
        st.caption(BACKTEST_HEADER)
    else:
        st.caption(f"Janela de calibração: do início da carteira até {_d(cfg.backtest.calibration_end)}.")
    frames = to_frames(rep)
    st.plotly_chart(charts.equity_chart(frames), width="stretch")
    st.dataframe(frames["diagnostics"], hide_index=True, width="stretch")


def render_glossary():
    st.markdown(
        """
- **Score de valuation (0–100):** soma ponderada de MVRV Z, preço/SMA200w, Puell, Pi Cycle, RSI semanal e Hash Ribbon.
- **Posição-base:** BTC da carteira no início do ciclo; base das metas de venda.
- **Venda acumulada-alvo:** quanto da posição-base o modelo recomenda ter vendido no ciclo (catraca; teto de 50%).
- **Reserva-base:** caixa em USD destinado a compras, fixado no início da campanha.
- **Fases:** ACUMULAR (reinício armado, compras pelo score), DISTRIBUIR (catraca > 0), MANTER.
- **Compra no reinício (modelo v2):** na semana em que um ciclo novo começa, comprar com todo o caixa disponível, incluindo o produto das vendas do ciclo anterior.
- **Detector de reversão:** independente do score; níveis N1 10%, N2 25%, N3 50%.
"""
    )


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------


def main():
    """Render the dashboard. Called on every Streamlit run (including reruns)."""
    st.set_page_config(page_title="BitSignal — Modelo de Ciclo", page_icon="⚡", layout="wide")
    st.title("⚡ BitSignal — Modelo de Ciclo Unificado")
    st.caption(f"Painel experimental · {model_label(get_config())} · só leitura · não executa ordens · "
               "os percentuais são referências do modelo, não ordens.")

    cfg = get_config()
    try:
        validate_for_panel(cfg)
    except ConfigError as exc:
        st.error(f"Config inválido para o painel ({exc.path}): {exc.message}")
        return

    now = now_utc()
    history = None
    try:
        history = load_history()
        st.session_state["last_good_history"] = history
    except Exception as exc:  # DataUnavailable, HTTP errors…
        st.session_state["last_attempt"] = now
        reason = "Dados da CoinMetrics indisponíveis" if isinstance(exc, DataUnavailable) else f"Falha ao buscar dados ({type(exc).__name__})"
        render_unavailable(cfg, reason, st.session_state.get("last_good_history"))
        return

    result = cached_model(f"{history.as_of}:{history.fetched_at}:{model_hash(cfg)}", history, cfg)
    if data_status(result, now, cfg) != DataStatus.OK:
        st.session_state["last_attempt"] = now
        render_unavailable(cfg, f"Dados desatualizados (última semana completa {_d(result.weeks.index[-1])})", history)
        return

    verdict = latest_verdict(result, now, cfg)
    if verdict.buy_all_cash:
        st.success("Ciclo novo nesta semana: comprar com **todo o caixa disponível** (inclui o produto das "
                   "vendas). O valor sai da sua planilha; o painel não conhece o seu caixa.")
    if verdict.phase == Phase.ACCUMULATE:
        st.success(f"Compra programada nesta semana: **{_pct(verdict.buy_pct) if verdict.buy_pct is not None else '—'}** da reserva-base (sujeita ao caixa disponível)")
        st.info(ACCUMULATE_NOTICE)
    st.markdown(top_line(verdict, cfg))
    render_spot()

    tab_week, tab_inputs, tab_cycle, tab_bt, tab_gloss = st.tabs(
        ["Semana", "Insumos", "Ciclo e eventos", "Backtest", "Glossário"]
    )
    last = result.weeks.iloc[-1]
    with tab_week:
        c1, c2 = st.columns(2)
        score_value = last["score"] if last["status"] == ScoreStatus.OK.value else last["score_min"]
        c1.plotly_chart(
            charts.score_gauge(score_value, cfg.sell_ladder, cfg.cycle.arm_score), width="stretch"
        )
        status = ScoreStatus(last["status"])
        if status != ScoreStatus.OK:
            c1.caption(f"Score em estado **{status.label}** (mín {last['score_min']:.1f} · máx {last['score_max']:.1f})"
                       if status == ScoreStatus.INTERVAL else "Score **indisponível** nesta semana.")
        c2.plotly_chart(charts.sell_target_gauge(verdict.sell_target, cfg.cap.cap), width="stretch")
        c2.caption(f"Venda acumulada-alvo: {_pct(verdict.sell_target)} de no máximo {_pct(cfg.cap.cap)} da posição-base.")
        render_detector(result)
        render_calculator(verdict, float(last["price"]))
    with tab_inputs:
        render_inputs(result, history, cfg)
        render_dune(history, cfg)
    with tab_cycle:
        render_cycle(result, verdict, cfg)
    with tab_bt:
        render_backtest(cfg)
    with tab_gloss:
        render_glossary()
    st.caption("Dados: CoinMetrics Community (CC BY-NC 4.0). Uso não comercial.")


# Streamlit Cloud may run this file directly as the app's main file. Streamlit executes it as
# __main__ on every run, so render here too; importing it (streamlit_app.py) does not call main().
if __name__ == "__main__":
    main()
