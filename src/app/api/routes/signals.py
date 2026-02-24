from fastapi import APIRouter
from ...infra.scheduler.jobs import store

router = APIRouter()

@router.get("/signals")
def signals():
    sigs = store.signals
    buy = sum(1 for s in sigs if s.decision == "AL")
    sell = sum(1 for s in sigs if s.decision == "SELL")
    wait = sum(1 for s in sigs if s.decision == "BEKLE")
    total = len(sigs) or 1

    summary = {
        "buyPct": round(buy * 100 / total, 1),
        "sellPct": round(sell * 100 / total, 1),
        "waitPct": round(wait * 100 / total, 1),
    }

    return {
        "count": len(sigs),
        "summary": summary,
        "lastUpdated": store.last_updated,
        "signals": [s.model_dump() for s in sigs],
        "warning": store.last_error,
    }