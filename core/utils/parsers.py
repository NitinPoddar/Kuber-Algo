# -*- coding: utf-8 -*-
"""
Created on Tue Aug 12 21:05:07 2025

@author: Home
"""



# utils/parsers.py (or inside your Wisdom client module)

def parse_pipe_candles(raw: str):
    """
    Parse 'ts|open|high|low|close|[volume]|[oi]|' records separated by commas.
    Returns list[dict] with keys: ts (ISO8601), open, high, low, close, volume.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    out = []
    if not raw:
        return out

    for rec in raw.strip().split(","):
        rec = rec.strip()
        if not rec:
            continue
        parts = [p for p in rec.split("|") if p != ""]  # remove empty after trailing |
        if not parts:
            continue

        ts_raw = parts[0]
        # must be an integer epoch; skip weird header rows like "7.45|..."
        if not ts_raw.isdigit():
            continue

        # seconds or milliseconds
        ts_int = int(ts_raw)
        if ts_int > 10**12:  # ms → s
            ts_int //= 1000

        try:
            o = float(parts[1]); h = float(parts[2]); l = float(parts[3]); c = float(parts[4])
        except (IndexError, ValueError):
            # incomplete/invalid bar → skip
            continue

        vol = 0
        if len(parts) > 5:
            try:
                vol = int(float(parts[5]))
            except Exception:
                vol = 0

        out.append({
            "ts": datetime.fromtimestamp(ts_int, ZoneInfo("Asia/Kolkata")).isoformat(),  # local system tz; adjust if needed
            "open": o, "high": h, "low": l, "close": c, "volume": vol,
        })

    out.sort(key=lambda r: r["ts"])
    return out
