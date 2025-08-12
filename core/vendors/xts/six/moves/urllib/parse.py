# -*- coding: utf-8 -*-
"""
Created on Mon Aug 11 21:28:02 2025

@author: Home
"""

# Minimal adapter for urllib.parse functions commonly imported via six
from urllib.parse import (
    urljoin, urlparse, urlsplit, urlunsplit, urlencode, quote, unquote, parse_qsl
)

__all__ = [
    "urljoin", "urlparse", "urlsplit", "urlunsplit",
    "urlencode", "quote", "unquote", "parse_qsl"
]
