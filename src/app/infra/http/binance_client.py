import asyncio
import random
import httpx
from typing import Any

class BinanceClient:
    def __init__(self, base_url: str, max_concurrency: int = 6):
        self.base_url = base_url.rstrip("/")
        self._sem = asyncio.Semaphore(max_concurrency)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(14.0, connect=9.0),
            headers={"Accept": "application/json", "User-Agent": "trader-bot/1.0"},
        )

    async def close(self):
        await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        async with self._sem:
            last_exc: Exception | None = None
            # exponential backoff + jitter
            for i in range(5):
                try:
                    r = await self._client.get(url, params=params)
                    # 429/5xx backoff
                    if r.status_code in (429, 418) or 500 <= r.status_code <= 599:
                        raise httpx.HTTPStatusError(f"upstream {r.status_code}", request=r.request, response=r)
                    r.raise_for_status()
                    return r.json()
                except Exception as e:
                    last_exc = e
                    sleep_s = min(6.0, (0.6 * (2 ** i)) + random.random() * 0.25)
                    await asyncio.sleep(sleep_s)
            raise last_exc or RuntimeError("unknown upstream error")
        
    async def exchange_info(self) -> dict:
        return await self._get("/fapi/v1/exchangeInfo")
    async def ping(self) -> dict:
        return await self._get("/fapi/v1/ping")

    async def ticker_24h(self) -> list[dict]:
        return await self._get("/fapi/v1/ticker/24hr")

    async def book_ticker(self, symbol: str) -> dict:
        return await self._get("/fapi/v1/ticker/bookTicker", params={"symbol": symbol})

    async def klines(self, symbol: str, interval: str, limit: int = 200) -> list[list[Any]]:
        # returns list of kline arrays
        return await self._get("/fapi/v1/klines", params={"symbol": symbol, "interval": interval, "limit": limit})

    async def open_interest_hist(self, symbol: str, period: str = "5m", limit: int = 30) -> list[dict]:
        # Futures data endpoint (USDT-M)
        # https://fapi.binance.com/futures/data/openInterestHist
        return await self._get(
            "/futures/data/openInterestHist",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
    
    