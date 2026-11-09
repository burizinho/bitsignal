"""Independent oracle for the reversal detector (design §5), version 2026-11-08 (S5 rewrite).

Offline and independent of the production code: uses only pandas/numpy and never imports
``bitsignal`` or ``probe.py``. Reads the frozen CoinMetrics CSV and writes the episodes as JSON:

    python docs/reviews/bitcoin_unified_cycle_model/sev.py \
        --csv data/historical/btc_coinmetrics.csv --out tests/golden/detector_episodes.json

Rules (§5, default config numbers):
  * weeks: Sundays (W-SUN) with a price, up to the last price date (closed weeks only);
    windows count valid weekly rows and require a full window (min_periods = window);
  * armed in week t if a new all-time high of the weekly close happened in the last 52 rows
    (incl. t); the first week is not an ATH;
  * trigger (opens an episode): armed, 2 consecutive closes < SMA30w, close <= 80% of the
    52-week max;
  * N2: 2 consecutive closes < SMA50w (may include the week before the trigger);
    N3: N2 reached (this week or earlier) and close <= 60% of the 52-week max;
  * order inside a week: trigger, N2, N3, closing test (not on the trigger week);
  * closing: 2 consecutive closes > SMA30w; ``end`` = closing week; an open episode has end null.
"""

import argparse
import json
import sys

import numpy as np
import pandas as pd

START = "2010-07-18"
ARMING, TREND, N2_SMA, CONFIRM = 52, 30, 50, 2
TRIGGER_RATIO, N3_RATIO = 0.80, 0.60


def weekly_closes(csv_path: str) -> pd.Series:
    df = pd.read_csv(csv_path, parse_dates=["date"], index_col="date").sort_index()
    last = df["price"].dropna().index[-1]
    cal = df.reindex(pd.date_range(START, last, freq="D"))
    price = cal["price"]
    sundays = price.index[(price.index.dayofweek == 6) & price.notna().to_numpy()]
    return price.loc[sundays]


def find_episodes(w: pd.Series) -> list:
    values = w.to_numpy(dtype=float)
    n = len(values)

    def rolling_mean(k):
        out = np.full(n, np.nan)
        for i in range(k - 1, n):
            out[i] = values[i - k + 1 : i + 1].mean()
        return out

    def rolling_max(k):
        out = np.full(n, np.nan)
        for i in range(k - 1, n):
            out[i] = values[i - k + 1 : i + 1].max()
        return out

    sma30, sma50, high52 = rolling_mean(TREND), rolling_mean(N2_SMA), rolling_max(ARMING)
    new_ath = [False] + [values[i] > values[:i].max() for i in range(1, n)]
    armed = [any(new_ath[max(0, i - ARMING + 1) : i + 1]) for i in range(n)]

    def held(cond, i):
        return i >= CONFIRM - 1 and all(cond(j) for j in range(i - CONFIRM + 1, i + 1))

    below30 = lambda j: values[j] < sma30[j]  # noqa: E731  (NaN comparisons are False)
    above30 = lambda j: values[j] > sma30[j]  # noqa: E731
    below50 = lambda j: values[j] < sma50[j]  # noqa: E731

    episodes, ep = [], None
    for i in range(n):
        day = w.index[i].date().isoformat()
        start_week = False
        if ep is None and armed[i] and held(below30, i) and values[i] <= TRIGGER_RATIO * high52[i]:
            ep = {"start": day, "n2": None, "n3": None, "end": None, "max_level": 1}
            start_week = True
        if ep is not None:
            if ep["n2"] is None and held(below50, i):
                ep["n2"], ep["max_level"] = day, 2
            if ep["n2"] is not None and ep["n3"] is None and values[i] <= N3_RATIO * high52[i]:
                ep["n3"], ep["max_level"] = day, 3
            if not start_week and held(above30, i):
                ep["end"] = day
                episodes.append(ep)
                ep = None
    if ep is not None:
        episodes.append(ep)
    return episodes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", required=True, help="frozen CoinMetrics CSV")
    ap.add_argument("--out", help="write JSON here (default: print)")
    args = ap.parse_args(argv)
    eps = find_episodes(weekly_closes(args.csv))
    text = json.dumps(eps, indent=2) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
