# -*- coding: utf-8 -*-
# core/services/brokers/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal

# ---- Common types -----------------------------------------------------------
Mode = Literal["paper", "live"]
Side = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT", "LIMIT_THEN_MARKET"]
TIF = Literal["DAY", "IOC"]

@dataclass
class Quote:
    symbol: str
    token: str
    ltp: float

@dataclass
class Candle:
    ts: str          # ISO8601
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class OrderRequest:
    token: str
    qty: int
    side: Side
    order_type: OrderType
    tif: TIF = "DAY"
    limit_price: Optional[float] = None
    product: str = "MIS"
    meta: Dict[str, Any] = None   # free-form per strategy (e.g., tag, client_order_id)

@dataclass
class OrderResult:
    broker_order_id: str
    status: Literal["New", "Replaced", "Filled", "Complete", "Rejected", "Cancelled", "Pending"]
    avg_price: Optional[float] = None
    raw: Dict[str, Any] = None

# ---- Abstract broker client -------------------------------------------------
class BrokerClient(ABC):
    """
    Minimal interface every broker adapter must implement.
    Concrete adapters translate these calls to each broker's SDK.
    """

    def __init__(self, account):
        # account is a BrokerAccount instance
        self.account = account

    # --- session / auth ---
    def authenticate(self) -> None:
        """Optional: establish a session / tokens. Default: no-op."""
        return None

    # --- market data ---
    @abstractmethod
    def fetch_candles(self, symbol: str, timeframe: str, lookback: int = 100) -> List[Candle]:
        """
        Return last `lookback` candles (oldest -> newest).
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_positions(self) -> List[Dict[str, Any]]:
        """
        Return current positions as a list of dicts (shape may vary by broker).
        """
        raise NotImplementedError

    def ltp(self, exchange: str, symbol: str, token: str) -> Quote:
        """
        Last traded price for a security. Implement if your broker supports it.
        """
        raise NotImplementedError

    def option_chain_greeks(self, name: str, expiry: str) -> List[Dict[str, Any]]:
        """
        Optional. Return greeks per strike/optionType if broker supports; otherwise raise.
        Expected items: {"strikePrice": float, "optionType": "CE|PE", "delta": float, ...}
        """
        raise NotImplementedError

    # --- orders ---
    def place(self, req: OrderRequest) -> OrderResult:
        """
        Place an order. Return broker-assigned id and initial status.
        """
        raise NotImplementedError
    
    def place_order(
        self, *, symbol: str, side: str, qty: int,
        order_type: str = "MARKET", price: Optional[float] = None,
        product: str = "MIS", validity: str = "DAY", tag: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Return at least {'order_id': str, 'status': 'accepted'|'rejected', ...}"""
        raise NotImplementedError
        
    def modify_order(
        self, order_id: str, *, price: Optional[float] = None, qty: Optional[int] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
       raise NotImplementedError

    def modify_to_limit(self, broker_order_id: str, new_price: float) -> OrderResult:
        """
        Convert/replace an order to LIMIT @ new_price (if supported).
        """
        raise NotImplementedError

    def modify_to_market(self, broker_order_id: str) -> OrderResult:
        """
        Convert/replace an order to MARKET (if supported).
        """
        raise NotImplementedError
    
    def fetch_orders(self) -> List[Dict[str, Any]]:
       raise NotImplementedError

    def status(self, broker_order_id: str) -> OrderResult:
        """
        Fetch current order status.
        """
        raise NotImplementedError
