import json
from typing import List
from datetime import datetime

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
    except Exception as e:
        store.last_error = f"DB hydrate error: {e}"

async def refresh_signals(market: MarketService):
    try:
        symbols = await market.get_top_symbols()
        signals: List[Signal] = []
        for s in symbols:
            sig = await market.build_signal_for(s)
            signals.append(sig)

        store.signals = signals
        store.last_error = None
        store.last_updated = datetime.utcnow().isoformat()

        payload = {
            "last_updated": store.last_updated,
            "warning": store.last_error,
            "signals": [s.model_dump() for s in store.signals],
        }
        await save_signals_snapshot(store.last_updated, json.dumps(payload))

    except Exception as e:
        store.last_error = str(e)