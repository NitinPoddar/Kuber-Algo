# -*- coding: utf-8 -*-
"""
Created on Mon Aug 11 10:30:21 2025

@author: Home
"""

# core/services/brokers/wisdom_capital.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import datetime as dt
import requests

from .base import BrokerClient

class WisdomCapitalClient(BrokerClient):
    """
    Minimal implementation for your system.
    Expects account.credentials to contain:
      {
        "api_key": "...",
        "api_secret": "...",          # if needed
        "access_token": "...",        # if they use OAuth, store refreshed token here
        "vendor_code": "...",         # whatever Wisdom needs
        "source": "...",              # any other required fields
      }
    """
    def __init__(self, account):
        super().__init__(account)
        self.root = (account.broker.root_api or "").rstrip("/")
        self.creds = account.credentials or {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Kuber/1.0"})
        # If the API needs an Authorization header:
        if "access_token" in self.creds:
            self.session.headers.update({"Authorization": f"Bearer {self.creds['access_token']}"})

        # small defaults
        self.timeout = 8

    # --- Market Data ---
    def fetch_candles(self, symbol: str, timeframe: str, lookback: int = 100) -> List[Dict[str, Any]]:
        """
        Convert your timeframe to their granularity, call their candles endpoint,
        and normalize to: ts, open, high, low, close, volume.
        """
        # Example URL shape — replace with Wisdom Capital docs:
        # GET {root}/market/candles?symbol=...&interval=5m&limit=100
        url = f"{self.root}/market/candles"
        params = {
            "symbol": symbol,
            "interval": timeframe,   # map "5m" → "5minute" if required
            "limit": lookback,
        }
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()

        candles = []
        for row in data.get("candles", []):
            # adapt field names to what Wisdom actually returns
            candles.append({
                "ts": row.get("ts") or row.get("time") or dt.datetime.utcnow().isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low":  float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            })
        return candles

    def fetch_positions(self) -> List[Dict[str, Any]]:
        url = f"{self.root}/positions"
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        # Return as-is or normalize shape
        return data.get("positions", data)

    # --- (Optional) Orders: flesh out when you’re ready ---
    def place_order(self, **order):
        url = f"{self.root}/orders"
        payload = self._build_order_payload(order)
        r = self.session.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _build_order_payload(self, o: Dict[str, Any]) -> Dict[str, Any]:
        # map your generic fields to Wisdom’s expected schema
        return {
            "symbol": o["symbol"],
            "side": o["side"],             # BUY/SELL mapping
            "qty": o["qty"],
            "type": o.get("type", "MARKET"),
            "limitPrice": o.get("price"),
            "product": o.get("product", "MIS"),
            # ...more fields per API
        }
