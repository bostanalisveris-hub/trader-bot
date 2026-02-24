from pydantic import BaseModel
import os

class Settings(BaseModel):
    # Binance Futures base
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://fapi.binance.com")

    # Top N
    top_n: int = int(os.getenv("TOP_N", "15"))

    # Scheduler (seconds)
    refresh_seconds: int = int(os.getenv("REFRESH_SECONDS", "60"))

    # Concurrency for HTTP calls
    max_concurrency: int = int(os.getenv("MAX_CONCURRENCY", "6"))

        # Eğer boş değilse sadece bu semboller kullanılacak (MVP için önerilen büyükler)
    symbol_whitelist_csv: str = os.getenv(
        "SYMBOL_WHITELIST",
        "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,BNBUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,LINKUSDT,TONUSDT,TRXUSDT,DOTUSDT,ATOMUSDT,NEARUSDT,LTCUSDT"
    )

    min_quote_volume_24h: float = float(os.getenv("MIN_QUOTE_VOL_24H", "50000000"))  # 50M USDT

settings = Settings()