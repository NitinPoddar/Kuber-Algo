# -*- coding: utf-8 -*-
"""
Created on Mon Aug 11 21:25:34 2025

@author: Home
"""
# Minimal shim for six – ONLY what we need for six.moves.urllib.parse.*
# Do NOT use this as a full replacement for six in general projects.

from __future__ import annotations
import sys

PY2 = False
PY3 = True

string_types = (str,)
text_type = str
binary_type = bytes

# Expose moves as a subpackage
from . import moves  # noqa: F401

__all__ = [
    "PY2", "PY3", "string_types", "text_type", "binary_type", "moves"
]

