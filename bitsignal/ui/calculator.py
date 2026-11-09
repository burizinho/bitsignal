"""Turns the verdict percentages into amounts, from numbers the user types in the dashboard.

Pure function, no Streamlit. Nothing is stored: the inputs live only in the browser session and
this is not a record of transactions. Fees and taxes are ignored (gross amounts).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bitsignal.models import Verdict


@dataclass(frozen=True)
class Amounts:
    sell_target_btc: Optional[float] = None  # cumulative sale target of the cycle, in BTC
    to_sell_btc: Optional[float] = None  # target minus what was already sold in the cycle
    to_sell_usd: Optional[float] = None
    buy_usd: Optional[float] = None
    buy_btc: Optional[float] = None
    buy_limited_by_cash: bool = False


def compute(verdict: Verdict, price: float, base_btc: float = 0.0, sold_btc: float = 0.0,
            reserve_usd: float = 0.0, cash_usd: float = 0.0) -> Amounts:
    """Zero means "not informed" for every input."""
    sell_target = to_sell = to_sell_usd = None
    if base_btc > 0 and verdict.sell_target is not None:
        sell_target = verdict.sell_target * base_btc
        to_sell = max(0.0, sell_target - max(0.0, sold_btc))
        to_sell_usd = to_sell * price

    buy_usd = None
    limited = False
    if verdict.buy_all_cash:
        buy_usd = cash_usd if cash_usd > 0 else None
    elif verdict.buy_pct and reserve_usd > 0:
        buy_usd = verdict.buy_pct * reserve_usd
        if cash_usd > 0 and buy_usd > cash_usd:
            buy_usd, limited = cash_usd, True
    buy_btc = buy_usd / price if buy_usd is not None and price > 0 else None
    return Amounts(sell_target, to_sell, to_sell_usd, buy_usd, buy_btc, limited)
