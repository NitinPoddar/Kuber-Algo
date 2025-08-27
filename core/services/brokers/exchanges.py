# -*- coding: utf-8 -*-
"""
Created on Mon Aug 25 21:33:28 2025

@author: Home
"""

# core/services/brokers/exchanges.py
from __future__ import annotations
from typing import Optional, Tuple
from core.models import Exchange, BrokerExchangeMap

def resolve_broker_code_and_segment(
    broker,
    logical_key: str,
) -> Tuple[Optional[str], Optional[int]]:
    """
    Returns (broker_code, xts_segment) for a given broker + our logical exchange key.
    broker_code may be None if no mapping exists; xts_segment may fall back to Exchange.default_xts_segment.
    Raises Exchange.DoesNotExist if logical_key is unknown to Exchange table.
    """
    exch = Exchange.objects.get(key=logical_key)  # raises if unknown

    # Per-broker mapping
    try:
        m = BrokerExchangeMap.objects.get(broker=broker, exchange=exch)
        seg = m.xts_segment if m.xts_segment is not None else exch.default_xts_segment
        return (m.broker_code, seg)
    except BrokerExchangeMap.DoesNotExist:
        return (None, exch.default_xts_segment)


def resolve_xts_segment_for_account(account, default_logical_key: str = "NSE_EQ") -> int:
    """
    Priority:
      1) account.credentials.exchange_segment (explicit override)
      2) BrokerExchangeMap.xts_segment for (broker, logical_key)
      3) Exchange.default_xts_segment
    Uses account.credentials.logical_exchange if present, else default_logical_key.
    """
    creds = getattr(account, "credentials", {}) or {}

    # 1) explicit per-account override
    seg = creds.get("exchange_segment")
    if seg is not None:
        try:
            return int(seg)
        except Exception:
            pass

    logical = (creds.get("logical_exchange") or default_logical_key).strip()
    _, seg = resolve_broker_code_and_segment(account.broker, logical)
    if seg is None:
        raise RuntimeError(
            f"No XTS exchangeSegment available for '{logical}'. "
            f"Set account.credentials.exchange_segment OR "
            f"add mapping/default for this exchange."
        )
    return int(seg)
