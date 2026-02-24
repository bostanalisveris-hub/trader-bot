import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .jobs import refresh_signals
from ...services.market_service import MarketService

def start_scheduler(market: MarketService, seconds: int):
    sched = BackgroundScheduler()

    def tick():
        # APScheduler sync çalışır; async job'u loop'ta koşturuyoruz
        asyncio.run(refresh_signals(market))

    sched.add_job(tick, IntervalTrigger(seconds=seconds), id="refresh_signals", replace_existing=True)
    sched.start()
    return sched