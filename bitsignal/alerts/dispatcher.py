"""Telegram alert dispatcher with multi-tier hysteresis and standardized runbooks."""

import logging
from typing import Optional
import requests
from bitsignal.models import AlertType, DailyCompositeResult, HysteresisState, SystemStatus
from bitsignal.storage.db import record_alert_dispatch

logger = logging.getLogger(__name__)


def build_telegram_message(
    result: DailyCompositeResult,
    alert_type: AlertType,
    sovereign_baseline_pct: float = 60.0,
) -> str:
    """Construct formatted Telegram Markdown message based on standardized runbooks."""
    date = result.date
    score = result.composite_score
    status = result.system_status.value

    top_contributors = sorted(
        result.metric_attribution.items(), key=lambda item: item[1], reverse=True
    )
    contrib_lines = "\n".join(
        [f"  • *{k.replace('_score', '').upper()}*: {v:.1f} pts" for k, v in top_contributors[:3]]
    )

    if alert_type == AlertType.TOP_TIER_1:
        return (
            f"🚨 *BITSIGNAL MACRO TOP WARNING (TIER 1)* 🚨\n\n"
            f"📅 *Date:* `{date}`\n"
            f"📊 *Composite Cycle Score:* `{score:.1f} / 100` (Status: `{status}`)\n\n"
            f"*Top Metric Drivers:*\n{contrib_lines}\n\n"
            f"📋 *ACTION RUNBOOK - TIER 1 (80-84):*\n"
            f"1. Stage a *20% divestment tranche* from cold storage to intermediate staging wallet.\n"
            f"2. Check mempool fee rates before broadcasting transfer.\n"
            f"3. Retain *80%* in sovereign cold storage.\n\n"
            f"🔒 *Permanent Hodl Baseline:* `{sovereign_baseline_pct:.0f}%` permanently reserved."
        )

    elif alert_type == AlertType.TOP_TIER_2:
        return (
            f"🚨 *BITSIGNAL MACRO TOP WARNING (TIER 2)* 🚨\n\n"
            f"📅 *Date:* `{date}`\n"
            f"📊 *Composite Cycle Score:* `{score:.1f} / 100` (Status: `{status}`)\n\n"
            f"*Top Metric Drivers:*\n{contrib_lines}\n\n"
            f"📋 *ACTION RUNBOOK - TIER 2 (85-89):*\n"
            f"1. Stage an additional *10% divestment tranche* (*30% cumulative exit*).\n"
            f"2. Deposit tranche to exchange order book with staged limit orders.\n"
            f"3. Retain *70%* in sovereign cold storage.\n\n"
            f"🔒 *Permanent Hodl Baseline:* `{sovereign_baseline_pct:.0f}%` permanently reserved."
        )

    elif alert_type == AlertType.TOP_TIER_3:
        return (
            f"🔥 *BITSIGNAL MAXIMUM EUPHORIA WARNING (TIER 3)* 🔥\n\n"
            f"📅 *Date:* `{date}`\n"
            f"📊 *Composite Cycle Score:* `{score:.1f} / 100` (Status: `{status}`)\n\n"
            f"*Top Metric Drivers:*\n{contrib_lines}\n\n"
            f"📋 *ACTION RUNBOOK - TIER 3 (>= 90):*\n"
            f"1. Stage final *10% divestment tranche* (*40% cumulative exit maximum*).\n"
            f"2. Execute final euphoria scale-out.\n"
            f"3. *CEASE FURTHER DIVESTMENT.* The remaining *60%* is the sovereign reserve.\n\n"
            f"🔒 *Permanent Hodl Baseline:* `{sovereign_baseline_pct:.0f}%` protected in cold custody."
        )

    elif alert_type == AlertType.BOTTOM_CAPITULATION:
        return (
            f"🟢 *BITSIGNAL MACRO BOTTOM ACCUMULATION* 🟢\n\n"
            f"📅 *Date:* `{date}`\n"
            f"📊 *Composite Cycle Score:* `{score:.1f} / 100` (Status: `{status}`)\n\n"
            f"*Metric Drivers:*\n{contrib_lines}\n\n"
            f"📋 *ACTION RUNBOOK - GENERATIONAL CAPITULATION (<= 20):*\n"
            f"1. Initiate staged DCA (Dollar-Cost Averaging) tranches.\n"
            f"2. Market valuation reflects generational macro capitulation.\n"
            f"3. Space out tranche accumulation over weekly intervals."
        )

    elif alert_type == AlertType.CIRCUIT_BREAKER:
        return (
            f"⚠️ *BITSIGNAL CIRCUIT BREAKER TRIPPED* ⚠️\n\n"
            f"📅 *Date:* `{date}`\n"
            f"Status: `CIRCUIT_BREAKER_TRIPPED`\n\n"
            f"Stale/Expired Metrics: `{result.stale_metrics or 'Unknown'}`\n\n"
            f"🚨 *Phase-transition trading alerts are FROZEN* to prevent distorted execution signals. "
            f"Investigate upstream API data sources."
        )

    return f"BitSignal Update [{date}]: Score = {score:.1f}"


def dispatch_telegram_alert(
    bot_token: Optional[str],
    chat_id: Optional[str],
    message: str,
    timeout: int = 10,
) -> bool:
    """Send markdown alert message to Telegram chat."""
    if not bot_token or not chat_id:
        logger.warning("Telegram bot_token or chat_id missing. Skipping push dispatch.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Failed to deliver Telegram alert: %s", exc)
        return False


def process_and_dispatch_alerts(
    result: DailyCompositeResult,
    previous_state: HysteresisState,
    bot_token: Optional[str],
    chat_id: Optional[str],
    db_path: str = "./data/bitsignal.db",
    dry_run: bool = False,
) -> Optional[AlertType]:
    """Determine if alert threshold was crossed under hysteresis rules and dispatch."""
    # 1. Circuit breaker takes priority
    if result.system_status == SystemStatus.CIRCUIT_BREAKER_TRIPPED:
        alert_type = AlertType.CIRCUIT_BREAKER
        msg = build_telegram_message(result, alert_type)
        if not dry_run:
            delivered = dispatch_telegram_alert(bot_token, chat_id, msg)
            record_alert_dispatch(result.date, alert_type.value, result.composite_score, msg, delivered, db_path)
        return alert_type

    # 2. Determine state transition under hysteresis rules
    curr = result.hysteresis_state
    alert_type = None

    if curr == HysteresisState.TOP_TIER_1 and previous_state not in (
        HysteresisState.TOP_TIER_1,
        HysteresisState.TOP_TIER_2,
        HysteresisState.TOP_TIER_3,
    ):
        alert_type = AlertType.TOP_TIER_1
    elif curr == HysteresisState.TOP_TIER_2 and previous_state != HysteresisState.TOP_TIER_2:
        alert_type = AlertType.TOP_TIER_2
    elif curr == HysteresisState.TOP_TIER_3 and previous_state != HysteresisState.TOP_TIER_3:
        alert_type = AlertType.TOP_TIER_3
    elif curr == HysteresisState.BOTTOM_CAPITULATION and previous_state != HysteresisState.BOTTOM_CAPITULATION:
        alert_type = AlertType.BOTTOM_CAPITULATION

    if alert_type:
        msg = build_telegram_message(result, alert_type)
        delivered = False
        if not dry_run:
            delivered = dispatch_telegram_alert(bot_token, chat_id, msg)
            record_alert_dispatch(result.date, alert_type.value, result.composite_score, msg, delivered, db_path)
        return alert_type

    return None
