# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 00:41:56 2025

@author: Home
"""

# services/billing.py
from core.models import Invoice, AlgoOffer, PlatformSetting

def compute_invoice_breakdown(*, offer: AlgoOffer, list_price_minor: int, discount_minor: int=0) -> dict:
    cfg = (PlatformSetting.objects.filter(key="billing").first() or None)
    platform_fee_pct = offer.platform_fee_pct
    gst_pct = (cfg.value.get("gst_pct", 18) if cfg else 18)
    tds_pct = (cfg.value.get("tds_pct", 0)  if cfg else 0)

    gross = max(0, int(list_price_minor))
    disc  = min(gross, int(discount_minor or 0))
    net   = gross - disc

    platform_fee = (net * platform_fee_pct) // 100
    creator_gross = net - platform_fee

    # If platform is the merchant of record, it charges GST on its *platform fee* portion
    gst = (platform_fee * gst_pct) // 100

    tds = (creator_gross * tds_pct) // 100  # if you need to withhold TDS

    creator_payout = creator_gross - tds
    return {
        "gross": gross, "discount": disc, "net": net,
        "platform_fee_pct": platform_fee_pct,
        "platform_fee": platform_fee,
        "creator_gross": creator_gross,
        "gst_pct": gst_pct, "gst": gst,
        "tds_pct": tds_pct, "tds": tds,
        "creator_payout": creator_payout
    }
