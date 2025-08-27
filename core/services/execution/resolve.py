# -*- coding: utf-8 -*-
"""
Created on Tue Aug 26 18:14:05 2025

@author: Home
"""

from django.db import transaction
from algos.models import InstrumentList, LegExecutionSnapshot

def resolve_leg_symbol(*, leg, ltp, strikes_for_name_expiry, udv_lookup):
    # 0) guard rails
    if not strikes_for_name_expiry:
        raise ValueError(f"No strikes for {leg.exchange_segment} {leg.instrument_name} {leg.expiry_date} {leg.option_type}")

    # 1) compute target_strike
    if leg.strike_kind == 'ABS':
        target_strike = float(leg.strike_price)
    else:
        nearest = min(strikes_for_name_expiry, key=lambda s: abs(float(s) - float(ltp)))
        if leg.strike_kind == 'ATM':
            target_strike = nearest
        else:  # OTM
            t = (leg.strike_target or '').strip()
            if t == '':
                raise ValueError("OTM selected but strike_target is empty")
            try:
                offset = float(t)
            except Exception:
                try:
                    offset = float(udv_lookup(t))
                except Exception as e:
                    raise ValueError(f"OTM target '{t}' is neither numeric nor a resolvable UDV") from e
            target_strike = nearest + offset
        target_strike = min(strikes_for_name_expiry, key=lambda s: abs(float(s) - float(target_strike)))

    # 2) fetch instrument (ensure option_type case matches your DB)
    qset = InstrumentList.objects.filter(
        exchange_segment=leg.exchange_segment,
        name=leg.instrument_name,
        expiry=leg.expiry_date,
        strike=target_strike,
        option_type=leg.option_type.upper(),   # if your table stores CE/PE uppercase
    )
    inst = qset.first()
    if not inst:
        raise ValueError(
            f"No instrument for {leg.exchange_segment} {leg.instrument_name} "
            f"{leg.expiry_date} strike {target_strike} {leg.option_type}"
        )
    lot_size = inst.lotsize or leg.lot_size_snapshot or 0
    return {
        "symbol": inst.symbol,
        "token": getattr(inst, "token", None),
        "strike": str(target_strike),
        "expiry": inst.expiry,
        "lot_size": int(lot_size),
    }

@transaction.atomic
def snapshot_leg_resolution(*, run, leg, attempt, resolved, extra_meta=None):
    return LegExecutionSnapshot.objects.create(
        run=run, leg=leg, attempt=attempt,
        resolved_symbol=resolved["symbol"],
        resolved_token=(resolved.get("token") or ""),
        resolved_expiry=resolved["expiry"],
        resolved_strike=resolved["strike"],
        lot_qty=leg.lot_qty, lot_size=resolved["lot_size"],
        option_type=leg.option_type, order_type=leg.order_type, order_direction=leg.order_direction,
        meta=(extra_meta or {}),
    )
