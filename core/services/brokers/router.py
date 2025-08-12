# core/services/brokers/router.py
from __future__ import annotations
from typing import Optional, Type
from importlib import import_module
from functools import lru_cache

from .base import BrokerClient
from .paper import PaperClient  # keep paper client import here

# Optional: legacy fallback mapping by substring in broker_name
_FALLBACK_MAP = {
    "wisdom": "core.services.brokers.wisdom_xts:WisdomClient",
    "zerodha": "core.services.brokers.zerodha.ZerodhaClient",
    "fyers":   "core.services.brokers.fyers.FyersClient",
    "angel":   "core.services.brokers.angel.AngelClient",
}

@lru_cache(maxsize=64)
def _load_adapter(path: str) -> Optional[Type[BrokerClient]]:
    try:
        module_name, class_name = path.rsplit(".", 1)
        module = import_module(module_name)
        cls = getattr(module, class_name)
        if not issubclass(cls, BrokerClient):
            return None
        return cls
    except Exception:
        return None

def _resolve_adapter_for_broker(broker) -> Optional[Type[BrokerClient]]:
    # 1) Preferred: explicit adapter_path set from the UI
    path = (getattr(broker, "adapter_path", "") or "").strip()
    if path:
        cls = _load_adapter(path)
        if cls:
            return cls

    # 2) Fallback: guess by broker_name substring
    name = (broker.broker_name or "").lower()
    for key, guess_path in _FALLBACK_MAP.items():
        if key in name:
            cls = _load_adapter(guess_path)
            if cls:
                return cls

    return None

def get_client_for_account(account) -> Optional[BrokerClient]:
    """
    Create a live client using Broker.adapter_path = 'pkg.mod:ClassName'.
    Returns None if we can't import/instantiate.
    """
    adapter = getattr(account.broker, "adapter_path", "") or ""
    if ":" in adapter:
        mod_path, cls_name = adapter.split(":", 1)
        try:
            mod = import_module(mod_path)
            cls = getattr(mod, cls_name)
            return cls(account)  # don't login yet; do it lazily in methods
        except Exception:
            return None

    # (Optional) Name-based fallbacks if you want:
    name = (account.broker.broker_name or "").lower()
    # if "zerodha" in name: from .zerodha import ZerodhaClient; return ZerodhaClient(account)
    return None

def get_paper_client(account: Optional[object] = None) -> BrokerClient:
    return PaperClient(account)
# Back-compat alias, if older code still imports get_client
