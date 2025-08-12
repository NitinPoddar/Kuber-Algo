# core/services/market_data.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.core.cache import cache


# -------- MOCKS --------
def fetch_candles_mock(symbol: str, timeframe: str = "5m", lookback: int = 100) -> List[Dict[str, Any]]:
    tf_minutes = int(timeframe.rstrip("m")) if timeframe.endswith("m") else 5
    now = datetime.utcnow()
    out = []
    price = 100.0
    for i in range(lookback, 0, -1):
        ts = now - timedelta(minutes=i * tf_minutes)
        o = price
        h = o + 0.8
        l = o - 0.8
        c = o + (0.2 if i % 2 else -0.2)
        v = 1000 + (i % 10) * 3
        out.append({"ts": ts.isoformat(), "open": round(o,2), "high": round(h,2),
                    "low": round(l,2), "close": round(c,2), "volume": v})
        price = c
    return out

def fetch_positions_mock() -> List[Dict[str, Any]]:
    return []

# -------- LIVE WRAPPERS --------
def fetch_candles_live(account, symbol: str, timeframe: str, lookback: int) -> List[Dict[str, Any]]:
    """
    Thin wrapper that selects the right adapter and caches briefly to avoid rate-limits.
    """
    from core.services.brokers.router import get_client_for_account
    key = f"ohlc:{account.id}:{symbol}:{timeframe}:{lookback}"
    cached = cache.get(key)
    if cached:
        return cached

    client = get_client_for_account(account)
    if not client:
        raise RuntimeError(f"No broker adapter for {account.broker.broker_name}")

    candles = client.fetch_candles(symbol, timeframe, lookback)
    # Basic sanity & shape
    if not isinstance(candles, list):
        raise RuntimeError("Broker returned malformed candles")
    cache.set(key, candles, timeout=3)  # 3s cache to be polite
    return candles

def fetch_positions_live(account) -> List[Dict[str, Any]]:
    from core.services.brokers.router import get_client_for_account
    client = get_client_for_account(account)
    if not client:
        raise RuntimeError(f"No broker adapter for {account.broker.broker_name}")
    return client.fetch_positions()
