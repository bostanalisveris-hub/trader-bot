from fastapi import FastAPI

from .settings import settings
from .infra.http.binance_client import BinanceClient
from .services.market_service import MarketService
from .infra.scheduler.runner import start_scheduler
from .api.routes.health import router as health_router
from .api.routes.signals import router as signals_router
from .api.routes.positions import router as positions_router

app = FastAPI(title="Futures Trader Bot API")

# Routers
app.include_router(health_router)
app.include_router(signals_router)
app.include_router(positions_router)

# Global objects
client: BinanceClient | None = None
scheduler = None

@app.on_event("startup")
async def startup():
    from .infra.storage.db import init_db
    from .infra.scheduler.jobs import hydrate_from_db
    await init_db()
    await hydrate_from_db()
    global client, scheduler
    client = BinanceClient(settings.binance_base_url, max_concurrency=settings.max_concurrency)
    wl = [s.strip().upper() for s in settings.symbol_whitelist_csv.split(",") if s.strip()]
    market = MarketService(
        client,
        top_n=settings.top_n,
        entry_tf="15m",
        max_spread_pct=0.12,
        whitelist=wl,
        min_quote_volume_24h=settings.min_quote_volume_24h,
    )

    # İlk snapshot hemen gelsin diye 1 kere çalıştır
    from .infra.scheduler.jobs import refresh_signals
    await refresh_signals(market)

    # Sonra periyodik refresh
    scheduler = start_scheduler(market, seconds=settings.refresh_seconds)

@app.on_event("shutdown")
async def shutdown():
    global client, scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
    if client:
        await client.close()