"""'O que mudaria o veredito': next triggers and today's distance (read-only explanation)."""

import pandas as pd

from bitsignal.config import load_config
from bitsignal.ui.whatif import what_would_change

V2 = load_config()
V1 = load_config("config/config_v1.yaml")


def weeks(rows):
    """rows: dicts overriding a calm default week; the last row is 'today'."""
    base = dict(price=100.0, trend_sma=90.0, n2_sma=80.0, high52w=110.0, ath=200.0, armed=False, level=0,
                score_min=50.0, score_max=50.0, status="OK", ratchet_sell=0.0, reset_pending=False)
    idx = pd.date_range("2027-01-03", periods=len(rows), freq="7D")
    return pd.DataFrame([{**base, **r} for r in rows], index=idx)


def text(rows, cfg=V2):
    return " | ".join(what_would_change(weeks(rows), cfg))


def test_accumulate_shows_restart_streak_and_v2_cash_buy():
    rows = [dict(reset_pending=True, score_min=31, score_max=31),
            dict(reset_pending=True, score_min=99, score_max=99, status="UNAVAILABLE"),  # neither counts nor breaks
            dict(reset_pending=True, score_min=12, score_max=12)]
    t = text(rows)
    assert "score mínimo ≥ 30 por 2 semanas" in t and "Hoje: 12.0 (0 de 2 semanas)" in t
    assert "compra com todo o caixa disponível" in t
    assert "compra com todo o caixa" not in text(rows, V1)  # v1 has no reset buy
    assert "4% da reserva-base por semana se o score máximo ficar ≤ 10" in t

    counting = [dict(reset_pending=True, score_min=31), dict(reset_pending=True, status="UNAVAILABLE", score_min=5),
                dict(reset_pending=True, score_min=35)]
    assert "(2 de 2 semanas)" in text(counting)


def test_no_bigger_buy_line_when_already_at_the_top_tier():
    assert "Compra maior" not in text([dict(reset_pending=True, score_min=8, score_max=8)])


def test_hold_shows_arming_streak_and_next_ladder_step():
    t = text([dict(score_max=18, score_min=18), dict(score_max=19, score_min=19)])
    assert "score máximo ≤ 20 por 2 semanas seguidas. Hoje: 19.0 (2 de 2 semanas)" in t
    assert "sobe para 5% se o score mínimo chegar a 85" in t


def test_ladder_top_step_and_cap():
    assert "já no último degrau (30%)" in text([dict(ratchet_sell=0.30)])
    assert "já está no teto de 50%" in text([dict(ratchet_sell=0.50)])


def test_detector_states():
    disarmed = text([dict(price=150.0, ath=200.0)])
    assert "desarmado" in disarmed and "US$ 200" in disarmed and "25.0% abaixo" in disarmed

    armed = text([dict(armed=True, price=85.0), dict(armed=True, price=86.0, ratchet_sell=0.15)])
    assert "Dispara no nível 1 (10%)" in armed and "(2 de 2 semanas abaixo da SMA30)" in armed
    assert "maior que a atual (15%)" in armed

    n1 = text([dict(armed=True, level=1, ratchet_sell=0.10)])
    assert "nível 2 (25%)" in n1 and "nível 3 (50%)" in n1 and "O episódio fecha" in n1

    n3 = text([dict(armed=True, level=3, ratchet_sell=0.50)])
    assert "Próximos" not in n3 and "maior que a atual" not in n3  # nothing above, already at the cap


def test_detector_is_neutralized_in_accumulate():
    assert "não aumenta a venda-alvo" in text([dict(reset_pending=True, score_min=12, score_max=12)])
