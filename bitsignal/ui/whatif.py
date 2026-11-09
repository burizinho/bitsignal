"""What would change the verdict: the next triggers of the model and how far the last week is.

Read-only explanation built from the last rows of ``ReplayResult.weeks`` and the config. It never
changes the verdict; it only states the rules of design §4–§6 next to today's values.
"""

from __future__ import annotations

from typing import List

import pandas as pd

from bitsignal.config import Config

UNAVAILABLE = "UNAVAILABLE"


def _f(x, digits: int = 1) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.{digits}f}"


def _usd(x) -> str:
    return "—" if x is None or pd.isna(x) else f"US$ {x:,.0f}"


def _pct(x) -> str:
    return f"{x * 100:.0f}%"


def _streak(weeks: pd.DataFrame, cond) -> int:
    """Consecutive most recent weeks meeting ``cond``; unavailable weeks neither count nor break."""
    n = 0
    for _, row in weeks.iloc[::-1].iterrows():
        if row["status"] == UNAVAILABLE:
            continue
        if not cond(row):
            break
        n += 1
    return n


def what_would_change(weeks: pd.DataFrame, cfg: Config) -> List[str]:
    """Markdown lines, one per trigger that can change the verdict from the last week."""
    last = weeks.iloc[-1]
    cyc = cfg.cycle
    ratchet = float(last["ratchet_sell"])
    smin, smax = last["score_min"], last["score_max"]
    lines: List[str] = []

    # Cycle: arm (score_max) or confirm the restart (score_min + detector at 0).
    if bool(last["reset_pending"]):
        k = _streak(weeks, lambda r: r["score_min"] >= cyc.confirm_score)
        tail = (" Nessa semana a venda-alvo volta a 0% e o modelo pede **compra com todo o caixa disponível**."
                if cfg.buys.on_reset == "all_cash" else " Nessa semana a venda-alvo volta a 0%.")
        lines.append(f"**Ciclo novo:** score mínimo ≥ {cyc.confirm_score:.0f} por {cyc.confirm_weeks} semanas seguidas, "
                     f"com o detector em 0. Hoje: {_f(smin)} ({min(k, cyc.confirm_weeks)} de {cyc.confirm_weeks} "
                     f"semanas).{tail}")
        tiers = sorted(cfg.buys.tiers)  # [(limit, pct)], lowest limit first
        current = next((p for lim, p in tiers if not pd.isna(smax) and smax <= lim), None)
        bigger = [(lim, p) for lim, p in tiers if current is None or p > current]
        if bigger:
            lim, p = bigger[-1]
            lines.append(f"**Compra maior:** {_pct(p)} da reserva-base por semana se o score máximo ficar ≤ {lim:.0f}. "
                         f"Hoje: {_f(smax)}.")
    else:
        k = _streak(weeks, lambda r: r["score_max"] <= cyc.arm_score)
        lines.append(f"**Fase ACUMULAR (compras):** score máximo ≤ {cyc.arm_score:.0f} por {cyc.arm_weeks} semanas "
                     f"seguidas. Hoje: {_f(smax)} ({min(k, cyc.arm_weeks)} de {cyc.arm_weeks} semanas).")

    # Sell ladder: next step above the current ratchet.
    cap = cfg.cap.cap
    if ratchet >= cap - 1e-12:
        lines.append(f"**Venda-alvo:** já está no teto de {_pct(cap)} da posição-base; só volta a 0% num ciclo novo.")
    else:
        step = next(((thr, p) for thr, p in cfg.sell_ladder if p > ratchet + 1e-12), None)
        if step is not None:
            thr, p = step
            lines.append(f"**Escada de venda:** a venda-alvo sobe para {_pct(min(p, cap))} se o score mínimo chegar a "
                         f"{thr:.0f}. Hoje: {_f(smin)}.")
        else:
            lines.append(f"**Escada de venda:** já no último degrau ({_pct(cfg.sell_ladder[-1][1])}). Só o detector "
                         f"pode elevar a venda-alvo, até {_pct(cap)}.")

    # Reversal detector.
    det = cfg.detector
    level = int(last["level"])
    price, trend, n2, high = last["price"], last["trend_sma"], last["n2_sma"], last["high52w"]
    neutral = " Enquanto a fase for ACUMULAR, ele não aumenta a venda-alvo." if bool(last["reset_pending"]) else ""
    levels = [0.0] + list(det.levels)
    only_if = (f" Um nível só muda a venda-alvo se for maior que a atual ({_pct(ratchet)})."
               if 0 < ratchet < cap - 1e-12 and not bool(last["reset_pending"]) else "")
    if level == 0 and not bool(last["armed"]):
        ath = last["ath"]
        gap = (1 - price / ath) * 100 if ath and not pd.isna(ath) else float("nan")
        lines.append(f"**Detector de reversão:** desarmado. Arma com um fechamento semanal acima da máxima histórica "
                     f"de {_usd(ath)} (hoje {_usd(price)}, {_f(gap)}% abaixo).{neutral}")
    elif level == 0:
        below = 0
        for _, r in weeks.iloc[::-1].iterrows():
            if not r["price"] < r["trend_sma"]:
                break
            below += 1
        lines.append(f"**Detector de reversão:** armado. Dispara no nível 1 ({_pct(min(levels[1], cap))}) com "
                     f"{det.confirm_weeks} fechamentos abaixo da SMA{det.trend_sma_weeks} semanal ({_usd(trend)}) e preço "
                     f"≤ {_usd(det.trigger_max_ratio_to_high52 * high)} (80% da máxima de 52 semanas). "
                     f"Hoje: {_usd(price)} ({min(below, det.confirm_weeks)} de {det.confirm_weeks} semanas abaixo "
                     f"da SMA{det.trend_sma_weeks}).{only_if}{neutral}")
    else:
        nxt = []
        if level == 1:
            nxt.append(f"nível 2 ({_pct(min(levels[2], cap))}) com {det.confirm_weeks} fechamentos abaixo da "
                       f"SMA{det.n2_sma_weeks} ({_usd(n2)})")
        if level <= 2:
            nxt.append(f"nível 3 ({_pct(min(levels[3], cap))}) depois do nível 2, com preço ≤ "
                       f"{_usd(det.n3_max_ratio_to_high52 * high)} (60% da máxima de 52 semanas)")
        close = (f"O episódio fecha com {det.confirm_weeks} fechamentos acima da SMA{det.trend_sma_weeks} "
                 f"({_usd(trend)}).")
        nxt_txt = ("Próximos: " + "; ".join(nxt) + ". ") if nxt else ""
        lines.append(f"**Detector de reversão:** episódio no nível {level}. {nxt_txt}{close} "
                     f"Hoje: {_usd(price)}.{only_if}{neutral}")
    return lines
