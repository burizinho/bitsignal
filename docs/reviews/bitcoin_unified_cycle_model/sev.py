"""Exploratory reproduction of the reversal-detector policy (Q5b) — version 2026-11-08.

Implements exactly the rules of §5 of docs/designs/bitcoin_unified_cycle_model.md:
  * armed in week t if a new all-time high of the weekly close happened in the last 52 weeks (incl. t);
  * an episode opens on an armed trigger: 2 consecutive weekly closes < SMA30w and close <= 80% of the 52-week max;
  * the episode closes after 2 consecutive weekly closes > SMA30w, even if arming expired meanwhile;
  * a new episode needs a new armed trigger (not a new ATH);
  * N1 = trigger (10%); N2 = N1 reached and 2 consecutive closes < SMA50w (25%);
    N3 = N2 reached (this week or earlier in the episode) and close <= 60% of the 52-week max (50%).

Exploratory script, NOT a validated test. Uses probe.py only to load CoinMetrics data (network required).
"""
import os

_here = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_here, "probe.py"), encoding="utf-8").read()
exec(_src.split('print("--- first crossings')[0].replace("print(", "(lambda *a, **k: None)("))

w = wk  # noqa: F821  (weekly closes, W-SUN, defined by probe.py)
sma30 = w.rolling(30).mean()
sma50 = w.rolling(50).mean()
hi52 = w.rolling(52).max()
ath = w.cummax()
new_ath = ath > ath.shift(1)
armed = new_ath.rolling(52, min_periods=1).max().astype(bool)
below30 = (w < sma30) & (w.shift() < sma30.shift())
below50 = (w < sma50) & (w.shift() < sma50.shift())
trigger = armed & below30 & (w <= 0.80 * hi52)

episodes = []
active = False
above = 0
for d in w.index:
    if not active:
        if trigger[d]:
            active = True
            ep = {"start": d, "n2": None, "n3": None}
            above = 0
    if active:
        if ep["n2"] is None and below50[d]:
            ep["n2"] = d
        if ep["n2"] is not None and ep["n3"] is None and w[d] <= 0.60 * hi52[d]:
            ep["n3"] = d
        if d != ep["start"]:
            above = above + 1 if w[d] > sma30[d] else 0
            if above >= 2:
                ep["end"] = d
                episodes.append(ep)
                active = False
if active:
    ep["end"] = w.index[-1]
    episodes.append(ep)

def fmt(d, ref):
    return f"{d.date()} {w[d]:,.0f} ({w[d] / ref:.0%} da máx. 52s)" if d is not None else "não"

for ep in episodes:
    if ep["start"] < __import__("pandas").Timestamp("2014-01-01"):
        continue
    ref = hi52[ep["start"]]
    fut = w.loc[ep["start"]:].iloc[1:79]
    lvl = "N3" if ep["n3"] is not None else ("N2" if ep["n2"] is not None else "N1")
    print(f"{ep['start'].date()} → {ep['end'].date()}  nível máx. {lvl}  | N1 {fmt(ep['start'], ref)} | N2 {fmt(ep['n2'], ref)} | N3 {fmt(ep['n3'], ref)} | 18m depois: máx {fut.max() / w[ep['start']]:.1f}x, mín {fut.min() / w[ep['start']]:.2f}x")
