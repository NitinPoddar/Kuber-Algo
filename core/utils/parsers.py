from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

def parse_pipe_ticks(raw: str):
    rows = []
    if not raw:
        return rows
    for rec in raw.strip().split(","):
        parts = [p for p in rec.strip().split("|") if p != ""]
        if len(parts) < 5:
            continue
        try:
            tsf = float(parts[0])
        except ValueError:
            continue
        if tsf > 10**12:  # ms -> s
            tsf /= 1000.0
        dt = datetime.fromtimestamp(tsf, UTC).astimezone(IST)
        try:
            o = float(parts[1]); h = float(parts[2]); l = float(parts[3]); c = float(parts[4])
        except Exception:
            continue
        v = int(float(parts[5])) if len(parts) > 5 and parts[5] not in ("", None) else 0
        rows.append({"dt": dt.replace(microsecond=0), "open": o, "high": h, "low": l, "close": c, "volume": v})
    rows.sort(key=lambda r: r["dt"])
    return rows

def in_nse_session(dt_ist: datetime) -> bool:
    s = dt_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    e = dt_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if dt_ist < s:  # simple prev-day check
        y = dt_ist - timedelta(days=1)
        s = y.replace(hour=9, minute=15, second=0, microsecond=0)
        e = y.replace(hour=15, minute=30, second=0, microsecond=0)
    return s <= dt_ist <= e

def aggregate_to_bars(rows, interval_min=5, filter_session=True):
    # merge duplicates within the same second
    merged = {}
    for r in rows:
        k = r["dt"]
        if filter_session and not in_nse_session(k):
            continue
        if k not in merged:
            merged[k] = r.copy()
        else:
            m = merged[k]
            m["high"] = max(m["high"], r["high"])
            m["low"]  = min(m["low"],  r["low"])
            m["close"] = r["close"]
            m["volume"] += r["volume"]

    # bucket to N-minute bars
    buckets = {}
    for dt, r in merged.items():
        dt = dt.replace(second=0)
        dt = dt.replace(minute=dt.minute - (dt.minute % interval_min))
        b = buckets.get(dt)
        if not b:
            buckets[dt] = {"open": r["open"], "high": r["high"], "low": r["low"], "close": r["close"], "volume": r["volume"]}
        else:
            b["high"] = max(b["high"], r["high"])
            b["low"]  = min(b["low"],  r["low"])
            b["close"] = r["close"]
            b["volume"] += r["volume"]

    return [{"ts": k.isoformat(timespec="seconds"),
             "open": v["open"], "high": v["high"], "low": v["low"], "close": v["close"], "volume": v["volume"]}
            for k, v in sorted(buckets.items())]
