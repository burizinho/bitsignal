"""Data models for national cycle strategy, tax planning, and portfolio tracking."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class StageType(str, Enum):
    # Accumulation stages
    C0 = "C0"  # 30% initial DCA allocation started at -30% ATH
    C1 = "C1"  # 15% allocation at -45% ATH
    C2 = "C2"  # 20% allocation at -55% ATH
    C3 = "C3"  # 20% allocation at -65% ATH or MVRV Z-Score <= 0.0
    C4 = "C4"  # 15% + remainder upon 50w SMA weekly breakout confirmation

    # Distribution stages
    V1 = "V1"  # 10% allocation upon breaking ATH (> ATH)
    V2 = "V2"  # 15% allocation at 1.3x ATH
    V3 = "V3"  # 15% allocation at 1.6x ATH
    V4 = "V4"  # 20% allocation at 2.0x ATH or 2/3 euphoria signals
    V5 = "V5"  # 20% allocation at 2.5x ATH

    # Trailing stop exits
    STOP_1 = "STOP_1"  # 50% remainder on 21w EMA weekly close break
    STOP_2 = "STOP_2"  # 100% remainder on 50w SMA weekly close break

    # Inter-month split completion
    SPLIT_PART_2 = "SPLIT_PART_2"  # Month-start pending split tranche execution


class StrategyPhase(str, Enum):
    ACCUMULATION = "ACCUMULATION"
    DISTRIBUTION = "DISTRIBUTION"
    COMPLETED = "COMPLETED"


class TaxStatus(str, Enum):
    EXEMPT = "EXEMPT"
    SPLIT_PENDING = "SPLIT_PENDING"
    TAXABLE = "TAXABLE"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PortfolioTransaction(BaseModel):
    id: Optional[int] = None
    date: str
    tx_type: TransactionType
    stage: StageType
    amount_btc: float = Field(gt=0)
    price_brl: float = Field(gt=0)
    price_usd: float = Field(gt=0)
    ptax_rate: Optional[float] = None
    fee_brl: float = 0.0
    exchange: str
    tx_hash: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


class PortfolioSummary(BaseModel):
    current_btc_balance: float
    current_cmp_brl: float
    total_invested_brl: float
    total_withdrawn_brl: float
    total_fees_brl: float = 0.0


class TaxExecutionPlan(BaseModel):
    action: str  # "SELL_FULL" or "SPLIT_MONTH_END"
    status: TaxStatus
    darf_amount: float = 0.0
    part1_now_brl: Optional[float] = None
    part2_next_month_brl: Optional[float] = None
    part1_btc: Optional[float] = None
    part2_btc: Optional[float] = None
    gross_gain_brl: float = 0.0
    notes: Optional[str] = None


class StrategyRunbook(BaseModel):
    stage: StageType
    date: str
    price_usd: float
    price_brl: float
    amount_btc: float
    amount_brl: float
    tax_plan: TaxExecutionPlan
    action_type: TransactionType
    order_type: str = "LIMIT"
    collar_price_brl: float
    nocturnal_pix_warning: bool = False
    instructions: List[str]
