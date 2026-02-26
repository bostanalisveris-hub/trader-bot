import asyncio
import json
import traceback
from typing import List
from datetime import datetime

from fastapi.encoders import jsonable_encoder

from ...domain.models import Signal
from ...services.market_service import MarketService
from ..storage.db import save_signals_snapshot, load_latest_signals_snapshot


class SignalStore:
    """In-memory + SQLite snapshot."""
    def __init__(self):
        self.signals: List[Signal] = []
        self.last_error: str | None = None
        self.last_updated: str | None = None


store = SignalStore()


async def hydrate_from_db():
    try:
        payload = await load_latest_signals_snapshot()
        if not payload:
            return
        data = json.loads(payload)
        sigs = [Signal(**s) for s in data.get("signals", [])]
        store.signals = sigs
        store.last_updated = data.get("last_updated")
        store.last_error = data.get("warning")
    except Exception:
        store.last_error = "DB hydrate error:\n" + traceback.format_exc()


async def refresh_signals(market: MarketService):
    try:
        symbols = await market.get_top_symbols()

        tasks = [market.build_signal_for(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals: List[Signal] = []
        for sym, res in zip(symbols, results):
            if isinstance(res, Exception):
                signals.append(Signal(
                    symbol=sym,
                    decision="BEKLE",
                    score=10,
                    daily_trend_ok=False,
                    updated_at=datetime.utcnow(),
                    plan=None,
                    reason=f"signal error: {type(res).__name__}",
                ))
            else:
                signals.append(res)

        store.signals = signals
        store.last_error = None
        store.last_updated = datetime.utcnow().isoformat()

        payload = {
            "last_updated": store.last_updated,
            "warning": store.last_error,
            "signals": [s.model_dump(mode="json") for s in store.signals],
        }

        encoded = jsonable_encoder(payload)
        await save_signals_snapshot(store.last_updated, json.dumps(encoded))

    except Exception:
        store.last_error = "refresh_signals error:\n" + traceback.format_exc()
