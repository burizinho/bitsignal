"""Unit tests for the national strategy cycle gauge calculations and figures."""

from bitsignal.ui.cycle_gauge import (
    get_all_stages_table,
    get_cycle_stage_info,
    render_cycle_regime_gauge,
    render_operational_intensity_gauge,
)


def test_cycle_stage_info_accumulation_stages():
    cycle_ath = 100000.0

    # C3: <= 35k (-65% ATH)
    info_c3 = get_cycle_stage_info(price_usd=34000.0, cycle_ath_usd=cycle_ath)
    assert info_c3["stage_id"] == "C3"
    assert info_c3["action"] == "COMPRA"
    assert info_c3["intensity_pct"] == 20.0
    assert info_c3["phase"] == "ACUMULAÇÃO (ENTRADA)"

    # C2: 35k < price <= 45k (-55% ATH)
    info_c2 = get_cycle_stage_info(price_usd=42000.0, cycle_ath_usd=cycle_ath)
    assert info_c2["stage_id"] == "C2"
    assert info_c2["action"] == "COMPRA"
    assert info_c2["intensity_pct"] == 20.0

    # C1: 45k < price <= 55k (-45% ATH)
    info_c1 = get_cycle_stage_info(price_usd=50000.0, cycle_ath_usd=cycle_ath)
    assert info_c1["stage_id"] == "C1"
    assert info_c1["action"] == "COMPRA"
    assert info_c1["intensity_pct"] == 15.0

    # C0: 55k < price <= 70k (-30% ATH)
    info_c0 = get_cycle_stage_info(price_usd=65000.0, cycle_ath_usd=cycle_ath)
    assert info_c0["stage_id"] == "C0"
    assert info_c0["action"] == "COMPRA"
    assert info_c0["intensity_pct"] == 30.0


def test_cycle_stage_info_neutral_zone():
    cycle_ath = 100000.0
    # Price between 70k and 100k
    info_neutral = get_cycle_stage_info(price_usd=85000.0, cycle_ath_usd=cycle_ath)
    assert info_neutral["stage_id"] == "NEUTRO"
    assert info_neutral["action"] == "NENHUMA (HODL)"
    assert info_neutral["intensity_pct"] == 0.0


def test_cycle_stage_info_distribution_stages():
    cycle_ath = 100000.0

    # V1: > 100k
    info_v1 = get_cycle_stage_info(price_usd=110000.0, cycle_ath_usd=cycle_ath)
    assert info_v1["stage_id"] == "V1"
    assert info_v1["action"] == "VENDA"
    assert info_v1["intensity_pct"] == 10.0

    # V2: >= 130k
    info_v2 = get_cycle_stage_info(price_usd=140000.0, cycle_ath_usd=cycle_ath)
    assert info_v2["stage_id"] == "V2"
    assert info_v2["intensity_pct"] == 15.0

    # V3: >= 160k
    info_v3 = get_cycle_stage_info(price_usd=170000.0, cycle_ath_usd=cycle_ath)
    assert info_v3["stage_id"] == "V3"
    assert info_v3["intensity_pct"] == 15.0

    # V4: >= 200k
    info_v4 = get_cycle_stage_info(price_usd=210000.0, cycle_ath_usd=cycle_ath)
    assert info_v4["stage_id"] == "V4"
    assert info_v4["intensity_pct"] == 20.0

    # V5: >= 250k
    info_v5 = get_cycle_stage_info(price_usd=260000.0, cycle_ath_usd=cycle_ath)
    assert info_v5["stage_id"] == "V5"
    assert info_v5["intensity_pct"] == 15.0


def test_render_figures_and_table():
    fig_regime = render_cycle_regime_gauge(current_price_usd=90000.0, cycle_ath_usd=126000.0)
    assert fig_regime is not None

    stage_info = get_cycle_stage_info(price_usd=90000.0, cycle_ath_usd=126000.0)
    fig_intensity = render_operational_intensity_gauge(stage_info)
    assert fig_intensity is not None

    df_table = get_all_stages_table(current_price_usd=90000.0)
    assert not df_table.empty
    assert len(df_table) == 11  # C3, C2, C1, C0, HODL, V1, V2, V3, V4, V5, Moonbag
