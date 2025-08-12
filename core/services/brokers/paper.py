# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 18:06:22 2025

@author: Home
"""

# core/services/brokers/paper.py
from typing import Optional
from .base import BrokerClient
from core.services.market_data import fetch_candles_mock, fetch_positions_mock

class PaperClient(BrokerClient):
    def __init__(self, account: Optional[object] = None):
        # keep interface same as real clients
        self.account = account

    def fetch_candles(self, symbol, timeframe, lookback=100):
        return fetch_candles_mock(symbol, timeframe, lookback)

    def fetch_positions(self):
        return fetch_positions_mock()
