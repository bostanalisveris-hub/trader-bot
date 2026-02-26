from fastapi import APIRouter
from ...infra.scheduler.jobs import store

router = APIRouter()

# Deploy kontrolü için (çıktıda görünmeli)
BUILD_TAG = "API-SIGNALS-2026-02-26-v7"

@router.get("/signals")
def signals():
    sigs = store.signals

    buy = sum(1 for s in sigs if str(s.decision) == "AL")
    sell = sum(1 for s in sigs if str(s.decision) == "SELL")
    wait = sum(1 for s in sigs if str(s.decision) == "BEKLE")
    total = len(sigs) or 1

    summary = {
        "buyPct": round(buy * 100 / total, 1),
        "sellPct": round(sell * 100 / total, 1),
        "waitPct": round(wait * 100 / total, 1),
    }

    return {
        "build": BUILD_TAG,  # ✅ bunu /signals çıktısında göreceksin
        "count": len(sigs),
        "summary": summary,
        "lastUpdated": store.last_updated,
        "signals": [s.model_dump(mode="json") for s in sigs],  # ✅ datetime-safe
        "warning": store.last_error,
    }

@router.get("/signals/_debug")
def signals_debug():
    return {
        "build": BUILD_TAG,
        "signals_count": len(store.signals),
        "last_updated": store.last_updated,
        "last_error": store.last_error,
        "file": __file__,
    }
