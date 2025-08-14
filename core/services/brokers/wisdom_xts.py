# -*- coding: utf-8 -*-
"""
Created on Mon Aug 11 11:22:04 2025

@author: Home
"""

# core/services/brokers/wisdom_xts.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .base import BrokerClient

# Try both import styles (pip vs vendored)
from core.vendors.xts.Connect import XTSConnect  # fallback if you vendor
import urllib
import json
from core.utils.parsers import aggregate_to_bars,parse_pipe_ticks

IST=ZoneInfo("Asia/Kolkata")
# Map your timeframe strings to XTS compressionValue (minutes)
_COMPRESSION = {
    "1m": 1, "3m": 3, "5m": 5, "10m": 10, "15m": 15, "30m": 30, "60m": 60,
    "1h": 60, "2h": 120, "day": 1440, "1d": 1440
}

try:
    needs_fetch = (instrument_list is None)
except NameError:
    needs_fetch = True

if needs_fetch:
    instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    with urllib.request.urlopen(instrument_url) as resp:
        instrument_list = json.load(resp)

def token_by_symbol(instruments, symbol):
    """Return the first token whose 'symbol' matches exactly (case-insensitive)."""
    symbol = (symbol or "").strip().upper()
    for row in instruments:
        if (row.get("symbol") or "").upper() == symbol:
            return row.get("token")
    return None



# Map your symbols -> instrument tokens (you can pass these in credentials)
def _resolve_token(symbol: str, creds: Dict[str, Any]) -> Optional[int]:
    # Prefer explicit mapping in BrokerAccount.credentials
    token_map = (creds.get("instrument_token_map") or {})
    tok = token_map.get(symbol) or token_map.get(symbol.upper())
    if tok:
        try:
            return int(tok)
        except Exception:
            pass
    # TODO: if you want, call XTS search endpoints here to resolve dynamically
    return None

def _tf_to_minutes(tf: str) -> int:
    tf = tf.lower().strip()
    return _COMPRESSION.get(tf, 5)

def _now_range_for(tf_minutes: int, lookback: int) -> tuple[str, str]:
    end = datetime.now(IST)
    # crude: assume 1 bar == tf_minutes; ask for lookback * tf
    start = end - timedelta(minutes=lookback * max(1, tf_minutes))
    fmt = "%b %d %Y %H%M%S"
    return start.strftime(fmt), end.strftime(fmt)

# core/services/brokers/wisdom_xts.py

# If you vendor the SDK in your project path, import it here
# from xts_api.xts_connect import XTSConnect  # example; adjust to your package

# core/services/brokers/wisdom_xts.py
class WisdomClient(BrokerClient):
    def __init__(self, account):
        super().__init__(account)
        self._session = None
        self._md_token = None
        self._user_id  = None
        self._xts  = None
        
    def _load_sdk(self):
        # 1) pip package
        
        # 2) vendored copy
        try:
            from core.vendors.xts.Connect import XTSConnect  # type: ignore
            return XTSConnect
        except Exception as e:
            raise RuntimeError(
                "XTS SDK not found. Install:\n"
                "  pip install xts-pythonclient_api_sdk\n"
                "or vendor it under core/vendors/xts/"
            ) from e
            
    def _ensure_login(self):
       
        if self._md_token:   # optionally check expiry too if you store it
            return self

        api  = self.account.credentials.get("market_api")
        sec  = self.account.credentials.get("market_secret")
        src  = self.account.credentials.get("source") or "WEBAPI"
        root = getattr(self.account.broker, "root_api", None) or "https://trade.wisdomcapital.in"

        if not api or not sec:
            raise RuntimeError("Wisdom credentials missing: set market_api & market_secret in account.credentials")
    
        if self._xts is None:
            self._xts = XTSConnect(apiKey=api, secretKey=sec, source=src, root=root)
    
        resp = self._xts.marketdata_login()
    
        # Normalize
        if isinstance(resp, str):
            raise RuntimeError(f"XTS login error: {resp}")
    
        if not resp or resp.get("type") != "success":
            desc = (resp or {}).get("description") if isinstance(resp, dict) else str(resp)
            raise RuntimeError(f"XTS login error: {desc}")
    
        result = resp.get("result") or {}
        self._md_token = result.get("token")
        self._user_id = result.get("userID")
        if not self._md_token:
            raise RuntimeError("XTS login did not return a token")

    
    def ping(self) -> Dict[str, Any]:
        self._ensure_login()
        return {"user_id": self._user_id,"token":self._md_token}

    
    

    # ---- required by BrokerClient ----
    def fetch_candles(self, symbol: str, timeframe: str, lookback: int = 100) -> List[Dict[str, Any]]:
        self._ensure_login() 
        #token = _resolve_token(symbol, self.credentials)
        token=token_by_symbol(instrument_list,symbol)
        if not token:
            raise RuntimeError(f"No XTS instrument token for symbol '{symbol}'. "
                               f"Provide credentials.instrument_token_map or implement search.")
        exchange_segment=self.account.credentials.get("exchange_segment")
        tf_min = _tf_to_minutes(timeframe)
        start, end = _now_range_for(tf_min, lookback)
        comp = tf_min

        resp = self._xts.get_ohlc(
            exchangeSegment=exchange_segment,
            exchangeInstrumentID=token,
            startTime=start,
            endTime=end,
            compressionValue=comp,
        )
        if not resp or resp.get("type") != "success":
            raise RuntimeError(f"get_ohlc failed: {resp!r}")

        # The SDK returns something like resp["result"]["dataReponse"] which may be JSON string or list
        result = resp.get("result", {})
        data = result.get("dataReponse") or result.get("dataResponse") or result.get("data") or []
        ticks = parse_pipe_ticks(data)  
        bars=aggregate_to_bars(ticks, interval_min=tf_min)
        return bars[-lookback:]
        #if isinstance(data, str):
         #   import json
          #  try:
           #     data = json.loads(data)
            #except Exception:
             #   data = []

        #out: list[dict[str, any]] = []
        # Try common shapes: {"Timestamp": "...", "Open":..., "High":..., "Low":..., "Close":..., "Volume":...}
        #for row in data:
         #   ts = (row.get("Timestamp") or row.get("time") or row.get("timestamp") or "").replace("T", " ")
          #  o = row.get("Open") or row.get("open")
           # h = row.get("High") or row.get("high")
            #l = row.get("Low") or row.get("low")
            #c = row.get("Close") or row.get("close")
            #v = row.get("Volume") or row.get("volume") or 0
            #if c is None:
             #   continue
            #out.append({"ts": ts, "open": float(o), "high": float(h), "low": float(l), "close": float(c), "volume": int(v)})
        # Oldest -> newest
        #out.sort(key=lambda r: r["ts"])
        #return out[-lookback:] if lookback else out

    def fetch_positions(self) -> List[Dict[str, Any]]:
        resp = self.xts.get_position_netwise()
        if not resp or resp.get("type") != "success":
            return []
        result = resp.get("result", {})
        rows = result.get("positionList") or result.get("positions") or []
        # Normalize minimally
        out = []
        for r in rows:
            out.append({
                "symbol": r.get("TradingSymbol") or r.get("Symbol"),
                "qty": r.get("NetQty") or r.get("Quantity") or 0,
                "avg_price": r.get("AveragePrice") or r.get("AvgPrice") or 0.0,
                "pnl": r.get("MTM") or r.get("PnL") or 0.0,
                "raw": r,
            })
        return out
