import math
from dataclasses import dataclass

from app.signals.naveen_v3 import StrategyConfig


@dataclass
class TradeLevels:
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    quantity: int
    capital_used: float
    risk_per_share: float
    total_risk: float
    capital_insufficient: bool = False


def calculate_levels(
    entry: float,
    atr: float,
    direction: str,
    config: StrategyConfig,
) -> TradeLevels:
    if direction == "BUY":
        stop = entry - atr * config.initial_stop_atr
        t1 = entry + atr * config.target1_atr
        t2 = entry + atr * config.target2_atr
        t3 = entry + atr * config.target3_atr
        risk_per_share = entry - stop
    else:
        stop = entry + atr * config.initial_stop_atr
        t1 = entry - atr * config.target1_atr
        t2 = entry - atr * config.target2_atr
        t3 = entry - atr * config.target3_atr
        risk_per_share = stop - entry

    qty = math.floor(config.capital_per_trade / entry) if entry > 0 else 0
    capital_used = qty * entry
    insufficient = qty == 0 and entry > config.capital_per_trade

    return TradeLevels(
        entry=round(entry, 2),
        stop_loss=round(stop, 2),
        target_1=round(t1, 2),
        target_2=round(t2, 2),
        target_3=round(t3, 2),
        quantity=qty,
        capital_used=round(capital_used, 2),
        risk_per_share=round(risk_per_share, 2),
        total_risk=round(risk_per_share * qty, 2),
        capital_insufficient=insufficient,
    )
