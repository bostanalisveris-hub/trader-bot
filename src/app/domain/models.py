from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class Decision(str, Enum):
    BUY = "AL"
    SELL = "SELL"
    WAIT = "BEKLE"

class Plan(BaseModel):
    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    rr: float | None = None

class Signal(BaseModel):
    symbol: str
    decision: Decision
    score: int  # 0..100
    daily_trend_ok: bool
    updated_at: datetime
    plan: Plan | None = None
    reason: str | None = None  # MVP: tek cümle gerekçe