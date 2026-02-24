from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

class NotEnoughData(Exception):
    pass

def ema(values: List[float], period: int) -> float:
    if len(values) < period:
        raise NotEnoughData(f"Not enough data for EMA({period})")
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = (v * k) + (e * (1 - k))
    return e

def rsi(values: List[float], period: int = 14) -> float:
    if len(values) < period + 1:
        raise NotEnoughData(f"Not enough data for RSI({period})")
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses += abs(diff)
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0.0)
        loss = max(-diff, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1 or len(highs) != len(lows) or len(lows) != len(closes):
        raise NotEnoughData(f"Not enough data for ATR({period})")
    trs: List[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        raise NotEnoughData(f"Not enough data for ATR({period})")
    return sum(trs[-period:]) / period