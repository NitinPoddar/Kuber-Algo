# -*- coding: utf-8 -*-
"""
Created on Wed Aug 27 15:02:19 2025

@author: Home
"""

from enum import Enum


class RuleType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    MANAGE = "MANAGE" # repair/modify/roll/scale
    UNIVERSAL_EXIT = "UNIVERSAL_EXIT" # global kill switch


class Scope(str, Enum):
    LEG = "LEG"
    ALGO = "ALGO"
    ACCOUNT = "ACCOUNT"


class TriggerEvent(str, Enum):
    ON_TICK = "on_tick"
    ON_BAR_CLOSE = "on_bar_close"
    ON_FILL = "on_fill"
    ON_TIMER = "on_timer"
    ON_RISK_EVENT = "on_risk_event"


class ActionType(str, Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    CLOSE_PARTIAL = "CLOSE_PARTIAL"
    MODIFY_ORDER = "MODIFY_ORDER"
    ROLL = "ROLL"
    SCALE_QTY = "SCALE_QTY"
    ADD_HEDGE = "ADD_HEDGE"
    FLATTEN_ALL = "FLATTEN_ALL"