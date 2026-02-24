from datetime import datetime
from typing import List

from ..domain.models import Signal, Decision, Plan
from ..domain.indicators import ema, rsi, atr, NotEnoughData
from ..infra.http.binance_client import BinanceClient
from ..infra.storage.cache import TTLCache

def _safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default

def _parse_klines(kl: list[list]):
    # kline format:
    # [openTime, open, high, low, close, volume, closeTime, quoteVol, trades, ...]
    closes, highs, lows = [], [], []
    for row in kl:
        closes.append(float(row[4]))
        highs.append(float(row[2]))
        lows.append(float(row[3]))
    return closes, highs, lows

class MarketService:
    def __init__(self, client: BinanceClient, top_n: int = 15, entry_tf: str = "15m", max_spread_pct: float = 0.12,
                 whitelist: list[str] | None = None, min_quote_volume_24h: float = 0.0):
        self.whitelist = whitelist or []
        self.min_quote_volume_24h = min_quote_volume_24h
        self.client = client
        self.top_n = top_n
        self.entry_tf = entry_tf
        self.max_spread_pct = max_spread_pct
        self._cache_1d = TTLCache(3600)     # 1 saat
        self._cache_1h = TTLCache(180)      # 3 dk
        self._cache_entry = TTLCache(60)    # 1 dk
        

    async def get_top_symbols(self) -> List[str]:
        # Eğer whitelist verilmişse direkt onu kullan
        if self.whitelist:
            return self.whitelist[: self.top_n]

        info = await self.client.exchange_info()
        allowed = set()
        for s in info.get("symbols", []):
            if s.get("quoteAsset") != "USDT":
                continue
            if s.get("contractType") != "PERPETUAL":
                continue
            if s.get("status") != "TRADING":
                continue
            allowed.add(s.get("symbol"))

        tickers = await self.client.ticker_24h()
        usdt = [t for t in tickers if t.get("symbol") in allowed]

        # min quote volume filtresi (illiquidleri at)
        if self.min_quote_volume_24h > 0:
            usdt = [t for t in usdt if _safe_float(t.get("quoteVolume")) >= self.min_quote_volume_24h]

        usdt.sort(key=lambda x: _safe_float(x.get("quoteVolume")), reverse=True)
        return [t["symbol"] for t in usdt[: self.top_n]]

    async def build_signal_for(self, symbol: str) -> Signal:
        now = datetime.utcnow()

        # -------- spread --------
        try:
            bt = await self.client.book_ticker(symbol)
            bid = _safe_float(bt.get("bidPrice"))
            ask = _safe_float(bt.get("askPrice"))
            mid = (bid + ask) / 2 if (bid and ask) else 0.0
            if bid <= 0 or ask <= 0:
                raise ValueError("bookTicker bid/ask invalid")
            spread_pct = ((ask - bid) / mid * 100.0) if mid > 0 else 999.0
        except Exception:
            return Signal(
                symbol=symbol,
                decision=Decision.WAIT,
                score=10,
                daily_trend_ok=False,
                updated_at=now,
                plan=None,
                reason="bookTicker alınamadı / likidite düşük",
            )

        if spread_pct > self.max_spread_pct:
            return Signal(
                symbol=symbol,
                decision=Decision.WAIT,
                score=15,
                daily_trend_ok=False,
                updated_at=now,
                plan=None,
                reason=f"Spread yüksek ({spread_pct:.3f}%)",
            )

        # -------- fetch klines --------
        # limits: daily needs 200 for EMA200, 1h needs 60-120, entry needs 120
               # -------- fetch klines (TTL cache) --------
        try:
            k1 = f"{symbol}:1d:220"
            k2 = f"{symbol}:1h:120"
            k3 = f"{symbol}:{self.entry_tf}:160"

            d1 = self._cache_1d.get(k1)
            if d1 is None:
                d1 = await self.client.klines(symbol, "1d", limit=220)
                self._cache_1d.set(k1, d1)

            h1 = self._cache_1h.get(k2)
            if h1 is None:
                h1 = await self.client.klines(symbol, "1h", limit=120)
                self._cache_1h.set(k2, h1)

            en = self._cache_entry.get(k3)
            if en is None:
                en = await self.client.klines(symbol, self.entry_tf, limit=160)
                self._cache_entry.set(k3, en)

        except Exception as e:
            return Signal(
                symbol=symbol,
                decision=Decision.WAIT,
                score=10,
                daily_trend_ok=False,
                updated_at=now,
                plan=None,
                reason=f"Veri çekilemedi: {e}",
            )

        try:
            d_close, d_high, d_low = _parse_klines(d1)
            h_close, h_high, h_low = _parse_klines(h1)
            e_close, e_high, e_low = _parse_klines(en)

            # -------- 1d regime --------
            d_ema50 = ema(d_close, 50)
            d_ema200 = ema(d_close, 200)
            daily_ok = (d_close[-1] > d_ema50) and (d_ema50 > d_ema200)

            # -------- 1h confirm --------
            h_ema50 = ema(h_close, 50)
            h_ok = (h_close[-1] > h_ema50)

            # -------- entry tf signals --------
            e_ema20 = ema(e_close, 20)
            e_ema50 = ema(e_close, 50)
            e_rsi = rsi(e_close, 14)
            e_atr = atr(e_high, e_low, e_close, 14)

            last = e_close[-1]

        except NotEnoughData as ne:
            return Signal(
                symbol=symbol,
                decision=Decision.WAIT,
                score=10,
                daily_trend_ok=False,
                updated_at=now,
                plan=None,
                reason=str(ne),
            )
        except Exception as e:
            return Signal(
                symbol=symbol,
                decision=Decision.WAIT,
                score=10,
                daily_trend_ok=False,
                updated_at=now,
                plan=None,
                reason=f"Parse/Calc hata: {e}",
            )

        # -------- Open Interest (opsiyonel) --------
        oi_score = 0
        try:
            oi = await self.client.open_interest_hist(symbol, period="5m", limit=30)
            if oi and len(oi) >= 5:
                # openInterest values are strings
                first = float(oi[0]["sumOpenInterest"])
                last_oi = float(oi[-1]["sumOpenInterest"])
                if first > 0:
                    change = (last_oi - first) / first
                    # pozitif artış küçük bonus
                    if change > 0.02:
                        oi_score = 8
                    elif change > 0.0:
                        oi_score = 4
                    elif change < -0.02:
                        oi_score = -6
                    else:
                        oi_score = -2
        except Exception:
            oi_score = 0  # fail-safe

        # -------- scoring (MVP weights) --------
        score = 50
        score += 15 if daily_ok else -10
        score += 10 if h_ok else -8
        score += 8 if e_ema20 > e_ema50 else -8
        score += 6 if e_rsi >= 55 else (-6 if e_rsi <= 45 else 0)
        score += oi_score

        # spread bonus (düşük spread iyi)
        score += 6 if spread_pct <= 0.05 else 0

        score = max(0, min(100, int(score)))

        # -------- plan (ATR based) --------
        # Basit plan: entry=last, stop = last - 1.3*ATR, target= last + 2.0*ATR
        entry = last
        stop = last - 1.3 * e_atr
        target = last + 2.0 * e_atr
        rr = (target - entry) / (entry - stop) if (entry - stop) > 0 else None

        plan = Plan(entry=entry, stop=stop, target=target, rr=rr)

        # -------- decision --------
        if score >= 70 and daily_ok and h_ok:
            decision = Decision.BUY
        elif score <= 35 and (not h_ok):
            decision = Decision.SELL
        else:
            decision = Decision.WAIT

        reason = f"1d:{'OK' if daily_ok else 'NO'} 1h:{'OK' if h_ok else 'NO'} EMA20/50:{'UP' if e_ema20>e_ema50 else 'DN'} RSI:{e_rsi:.1f} OI:{oi_score}"

        return Signal(
            symbol=symbol,
            decision=decision,
            score=score,
            daily_trend_ok=daily_ok,
            updated_at=now,
            plan=plan,
            reason=reason,
        )