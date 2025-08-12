# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 13:32:25 2025

@author: Home
"""

# core/services/brokers/zerodha.py
from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime, timedelta, timezone

from .base import BrokerClient

def _map_timeframe(tf: str) -> str:
    """
    Map '1m','3m','5m','15m','30m','60m','day' -> Zerodha/Kite's "minute" granularity.
    """
    tf = tf.lower()
    if tf.endswith("m"):  # minute granularity
        return "minute"   # we'll fetch N*minutes range and group if needed (simple approach)
    if tf in ("1h","60m"):
        return "minute"   # still minute; we'll request 60-min range and post-aggregate if you want (optional)
    if tf in ("day","1d","d"):
        return "day"
    return "minute"

class ZerodhaClient(BrokerClient):
    """
    Very small adapter. Requires `kiteconnect` installed and credentials present.
    credentials expected keys:
      - api_key
      - access_token   (or a refresh flow you manage elsewhere)
    """
    def __init__(self, account):
        super().__init__(account)
        try:
            from kiteconnect import KiteConnect  # type: ignore
        except Exception:
            self._kite_cls = None
        else:
            self._kite_cls = KiteConnect
        self._kite = None

    def _ensure_session(self):
        if not self._kite_cls:
            raise RuntimeError("kiteconnect not installed. `pip install kiteconnect`")
        api_key = (self.account.credentials or {}).get("api_key")
        access_token = (self.account.credentials or {}).get("access_token")
        if not api_key or not access_token:
            raise RuntimeError("Missing Zerodha credentials (api_key/access_token).")
        kite = self._kite_cls(api_key=api_key)
        kite.set_access_token(access_token)
        self._kite = kite

    def fetch_candles(self, symbol: str, timeframe: str, lookback: int = 100) -> List[Dict[str, Any]]:
        self._ensure_session()
        tf_kind = _map_timeframe(timeframe)

        # naive range: last N*tf minutes or days (kept simple for test)
        now = datetime.now(timezone.utc)
        if tf_kind == "day":
            frm = now - timedelta(days=lookback + 5)
            to  = now
            interval = "day"
        else:
            # minute range (pad generously)
            minutes = int(timeframe.rstrip("m")) if timeframe.endswith("m") else 5
            frm = now - timedelta(minutes=lookback*minutes + 50)
            to  = now
            interval = "minute"

        # Zerodha requires instrument_token; for this test path
        # assume `symbol` is tradingsymbol and you have mapping → token elsewhere.
        # If you maintain a map in globals, read it here. For demo, we'll try "NSE:XYZ" style via historical_data?
        #
        # In a real setup you'll resolve tradingsymbol → instrument_token first.

        # PSEUDO: instrument_token = resolve_token(symbol)
        instrument_token = (self.account.credentials or {}).get("instrument_token")
        if not instrument_token:
            # If you don't have a token, you must implement resolution beforehand.
            raise RuntimeError("instrument_token missing; please resolve symbol → instrument token first.")

        data = self._kite.historical_data(instrument_token, frm, to, interval)  # list of dicts
        out = []
        for row in data[-lookback:]:  # just keep last `lookback`
            out.append({
                "ts": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row.get("volume", 0)),
            })
        return out

    def fetch_positions(self) -> List[Dict[str, Any]]:
        self._ensure_session()
        pos = self._kite.positions()
        # pos = {"day": [...], "net": [...]}
        # normalize to a flat list
        return pos.get("net", [])
