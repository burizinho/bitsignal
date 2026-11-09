"""Backtest output (plan item 32): text for the CLI, frames for the dashboard, golden summary.

Golden summary (calibration window only):
    python -m bitsignal.backtest.report --golden tests/golden/replay_summary.json
"""

from __future__ import annotations

import argparse
import json
from typing import Dict

import pandas as pd

from bitsignal.models import EventType

HEADER = "2019 até o congelamento é validação histórica de desenvolvimento, não amostra independente."


def _pct(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.1f}%"


def to_text(report) -> str:
    lines = [
        "=" * 72,
        f"BitSignal — backtest ({report.window})   {report.start} → {report.end}",
        HEADER,
        f"model_hash {report.model_hash[:12]}…   csv {str(report.csv_sha256)[:12]}…",
        "=" * 72,
    ]
    if report.criteria is None:
        lines.append("Critérios Q1: não calculados nesta janela (só depois do congelamento, janela de desenvolvimento).")
    else:
        v, p = report.criteria["values"], report.criteria["passed"]
        ok = lambda b: "APROVADO" if b else "NÃO APROVADO"  # noqa: E731
        lines += [
            "Critérios Q1 (rebaseados em 2019-01-01):",
            f"  1. patrimônio / comprar e segurar = {v['equity_vs_bnh']:.3f}  → {ok(p['equity_vs_bnh'])}",
            f"  2. melhora da queda máxima = {v['dd_improvement_pp']:.1f} p.p.  → {ok(p['dd_improvement_pp'])}",
            f"  3. patrimônio / DCA uniforme = {v['equity_vs_uniform']:.3f}  → {ok(p['equity_vs_uniform'])}",
        ]
    s = report.diagnostics["summary"]
    lines += ["", "Resumo da janela (USD, queda máxima em p.p.):"]
    for k, name in (("strategy", "estratégia"), ("bnh", "comprar e segurar"), ("uniform", "DCA uniforme")):
        lines.append(f"  {name:<18} patrimônio final {s[k]['equity_end_usd']:>14,.0f}   queda máx {s[k]['max_dd_pp']:5.1f}")
    ps, fs = report.diagnostics["premature_sales"], report.diagnostics["false_sells"]
    lines += [
        "",
        f"Venda prematura: {_pct(ps['pct_btc_premature'])} do BTC vendido (excluídas {ps['excluded']})",
        f"Vendas falsas: {fs['count']} (custo {fs['cost_btc']:.4f} BTC; excluídas {fs['excluded']})",
        f"Reinícios falsos: {report.false_resets}",
        "",
        "Eventos de diagnóstico:",
    ]
    for _, r in report.diagnostics["events"].iterrows():
        if not r.get("evaluable", False):
            lines.append(f"  {r['event']:<14} fora da janela")
        else:
            lines.append(f"  {r['event']:<14} {r['kind']:<6} {_pct(r['pct'])}  preço médio {r['avg_price']:,.0f}")
    if report.sensitivities:
        lines += ["", "Sensibilidades:"]
        for name, e in report.sensitivities.items():
            if not e.get("applicable"):
                lines.append(f"  {name:<16} {e.get('reason')}")
            else:
                lines.append(f"  {name:<16} patrimônio final {e['strategy']['equity_end_usd']:,.0f}   queda máx {e['strategy']['max_dd_pp']:.1f}")
    return "\n".join(lines)


def to_frames(report) -> Dict[str, pd.DataFrame]:
    eq = pd.DataFrame(
        {
            "estratégia": report.strategy.equity["equity_usd"],
            "comprar e segurar": report.bnh.equity["equity_usd"],
            "DCA uniforme": report.uniform.equity["equity_usd"],
        }
    )
    crit = pd.DataFrame()
    if report.criteria is not None:
        crit = pd.DataFrame({"valor": report.criteria["values"], "aprovado": report.criteria["passed"]})
    return {
        "criteria": crit,
        "diagnostics": report.diagnostics["events"],
        "equity": eq,
        "phases": report.weeks[["price", "phase", "ratchet_sell", "buy_pct"]],
    }


def golden_summary(report) -> dict:
    """Calibration-window regression summary used by tests/test_golden.py."""
    s = report.diagnostics["summary"]
    return {
        "cycle_starts": [e.date.isoformat() for e in report.events if e.type == EventType.CYCLE_START],
        "sell_steps": [
            {"date": e.date.isoformat(), "mechanism": e.mechanism, "after": round(e.after, 6)}
            for e in report.events
            if e.type == EventType.SELL_STEP
        ],
        "calibration": {
            "strategy_equity_end": s["strategy"]["equity_end_usd"],
            "bnh_equity_end": s["bnh"]["equity_end_usd"],
            "uniform_equity_end": s["uniform"]["equity_end_usd"],
            "strategy_max_dd": s["strategy"]["max_dd_pp"],
        },
    }


def _main(argv=None):
    from bitsignal.backtest.engine import run_backtest
    from bitsignal.config import load_config
    from bitsignal.data.history import load_frozen_history

    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", required=True)
    args = ap.parse_args(argv)
    cfg = load_config()
    rep = run_backtest(load_frozen_history(cfg.data.csv_path), cfg, window="calibration", sensitivities=False)
    with open(args.golden, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(golden_summary(rep), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    _main()
