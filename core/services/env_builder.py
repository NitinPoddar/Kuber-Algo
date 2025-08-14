# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 13:16:56 2025

@author: Home
"""


# ---- Public API -------------------------------------------------------------

# core/services/env_builder.py
from __future__ import annotations
from typing import Any, Dict, Optional

from django.utils import timezone
from django.contrib.auth import get_user_model

from core.models import (
    GlobalVariable,
    BrokerAccount,
    AlgoBrokerLink,
    # AlgorithmLogic,  # ← unused; remove
)

UserT = get_user_model()

def build_env(user: UserT,algo_id: Optional[int],*,mode: str = "paper",account_id: Optional[int] = None,include_helpers: bool = True,) -> Dict[str, Any]:
    # Local import avoids circulars if other modules import env_builder
    from core.services.brokers.router import get_client_for_account, get_paper_client

    mode = (mode or "paper").lower()
    g = merge_scoped_globals(user, algo_id if algo_id is not None else -1)

    broker_payload: Optional[Dict[str, Any]] = None
    client = None

    acc: Optional[BrokerAccount] = None
    if account_id is not None or mode in ("paper", "live"):
        acc = pick_account_for_mode(user, algo_id, mode, account_id=account_id)
        if acc:
            broker_payload = {
                "account_id": acc.id,
                "label": acc.label,
                "username": acc.broker_username,
                "broker": {
                    "id": acc.broker_id,
                    "name": acc.broker.broker_name,
                    "root_api": acc.broker.root_api,
                },
            }
            g.setdefault("runtime", {})["active_broker_account_id"] = acc.id

    # Attach a client
    client = None
    client_err = None
    try:
        
        if mode == "paper":
            client = get_paper_client(account=acc)  # ok if acc is None
        elif acc:
            client = get_client_for_account(account=acc)
    except Exception as e:
            client_err = f"{type(e).__name__}: {e}"
    
    return {
        "globals": g,
        "broker": broker_payload,
        "client": client,
        "helpers": default_helpers() if include_helpers else {},
        "meta": {
            "algo_id": algo_id,
            "user_id": user.id,
            "ts": timezone.now().isoformat(),
            "mode": mode,
        },
    }


def merge_scoped_globals(user: UserT, algo_id: Optional[int]) -> Dict[str, Any]:
    """
    Precedence: global < algo < user (user overrides everything).
    If algo_id is None, we just skip algo-level overrides.
    """
    merged: Dict[str, Any] = {}

    for gv in GlobalVariable.objects.filter(algo__isnull=True, user__isnull=True):
        merged[gv.key] = normalize_value(gv)

    if algo_id is not None:
        for gv in GlobalVariable.objects.filter(algo_id=algo_id, user__isnull=True):
            merged[gv.key] = normalize_value(gv)

    for gv in GlobalVariable.objects.filter(user=user, algo__isnull=True):
        merged[gv.key] = normalize_value(gv)

    return merged


def pick_account_for_mode(
    user: UserT,
    algo_id: Optional[int],
    mode: str,
    *,
    account_id: Optional[int] = None,
) -> Optional[BrokerAccount]:
    # explicit wins
    if account_id:
        try:
            return BrokerAccount.objects.get(id=account_id)
        except BrokerAccount.DoesNotExist:
            return None

    if algo_id is None:
        # No algo context → cannot derive from links
        return None

    q = AlgoBrokerLink.objects.filter(user=user, algo_id=algo_id)
    if mode == "paper":
        link = q.filter(role="paper", is_default=True).first() or q.filter(role="paper").first()
        return link.account if link else None

    live_q = q.exclude(role="paper")
    link = (live_q.filter(is_default=True).first()
            or live_q.filter(role="primary", is_default=True).first()
            or live_q.filter(role="primary").first()
            or live_q.first())
    return link.account if link else None


# ---- Internals / utilities --------------------------------------------------

def normalize_value(gv: GlobalVariable) -> Any:
    """
    Optionally normalize number dtype to Python number if stored as string.
    (Safe no-op for text/json)
    """
    if gv.dtype == "number" and isinstance(gv.value, str):
        try:
            num = float(gv.value) if "." in gv.value else int(gv.value)
            return num
        except Exception:
            return gv.value
    return gv.value


# core/services/env_builder.py
def default_helpers() -> Dict[str, Any]:
    import math
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        ZoneInfo = None

    def now_tz(tz_name: str = "Asia/Kolkata"):
        """
        Return a small dict with the current time in the given timezone.
        No network, safe to expose in sandbox.
        """
        if ZoneInfo:
            dt = datetime.now(ZoneInfo(tz_name))
        else:
            # Fallback for Windows/Py<3.9: naive UTC (or quick IST adjustment)
            from datetime import timezone, timedelta
            dt = datetime.now(timezone.utc)
            if tz_name in ("Asia/Kolkata", "IST"):
                dt = dt + timedelta(hours=5, minutes=30)
        return {
            "iso": dt.isoformat(),
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M:%S"),
            "weekday": dt.weekday(),
            "hour": dt.hour,
            "minute": dt.minute,
        }

    def in_session_now(session: dict) -> bool:
        tz_name = session.get("timezone", "Asia/Kolkata")
        t = now_tz(tz_name)["time"]  # "HH:MM:SS"
        hh, mm, _ = t.split(":")
        cur = int(hh) * 60 + int(mm)
        def _mins(s: str): 
            h, m = s.split(":"); return int(h) * 60 + int(m)
        try:
            s = _mins(session.get("start", "00:00"))
            e = _mins(session.get("end", "23:59"))
            return s <= cur <= e
        except Exception:
            return True

    def clamp(x, lo, hi): 
        return max(lo, min(hi, x))

    return {"math": math, "now_tz": now_tz, "in_session_now": in_session_now, "clamp": clamp}
