"""CSV export for the user's spreadsheet: this week's verdict and the recorded weekly log.

Not a record of transactions: only what the model said. Two formats:
* ``brazil=True`` (default in the dashboard): ``;`` separator and decimal comma, which Excel and
  Google Sheets in Portuguese open directly;
* ``brazil=False``: ``,`` separator and decimal point.
UTF-8 with BOM, so Excel shows the accents in the ``reason`` column.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from bitsignal.verdict_log import COLUMNS

_DECIMAL = re.compile(r"^-?\d+\.\d+$")


def _localize(value: str, brazil: bool) -> str:
    if brazil and _DECIMAL.match(value or ""):
        return value.replace(".", ",")
    return value


def rows_to_csv(rows: List[Dict[str, str]], brazil: bool = True) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, delimiter=";" if brazil else ",", lineterminator="\r\n",
                       extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: _localize(str(r.get(k, "")), brazil) for k in COLUMNS})
    return ("﻿" + buf.getvalue()).encode("utf-8")


def read_log(path: Union[str, Path]) -> Optional[List[Dict[str, str]]]:
    p = Path(path)
    if not p.exists():
        return None
    with io.open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
