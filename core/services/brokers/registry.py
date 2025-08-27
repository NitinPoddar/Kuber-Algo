from __future__ import annotations
from importlib import import_module
from typing import Optional, Type
from .base import BrokerClient
# re-export helpers so adapters can do: from core.services.brokers.router import resolve_xts_segment_for_account
from .exchanges import resolve_broker_code_and_segment, resolve_xts_segment_for_account

def _import_adapter(path: str) -> Optional[Type[BrokerClient]]:
    if not path:
        return None
    try:
        if ":" in path:
            module_path, class_name = path.split(":", 1)
        else:
            module_path, class_name = path.rsplit(".", 1)
        mod = import_module(module_path)
        cls = getattr(mod, class_name)
        return cls
    except Exception:
        return None

def get_paper_client(account=None) -> BrokerClient:
    from .paper import PaperClient
    return PaperClient(account)

def get_client_for_account(account) -> Optional[BrokerClient]:
    # 1) Prefer explicit adapter path from DB
    path = getattr(account.broker, "adapter_path", None)
    cls = _import_adapter(path) if path else None
    if cls:
        try:
            return cls(account)
        except Exception:
            return None

    # 2) Fallback: name-based routing
    name = (account.broker.broker_name or "").lower()
    if "zerodha" in name:
        from .zerodha import ZerodhaClient
        return ZerodhaClient(account)
    if "wisdom" in name or "xts" in name:
        from .wisdom_xts import WisdomClient
        return WisdomClient(account)

    return None
