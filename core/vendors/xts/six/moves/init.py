# -*- coding: utf-8 -*-
"""
Created on Mon Aug 11 21:26:50 2025

@author: Home
"""

# Keep this minimal – we only need the urllib subpackage path to resolve.
# Imports like `from six.moves.urllib.parse import urljoin` will work
# because we provide the package structure.

# Optionally expose `urllib` as an attribute for `from six.moves import urllib`
from . import urllib  # noqa: F401

__all__ = ["urllib"]
