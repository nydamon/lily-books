"""Retailer upload integrations for distribution.

Stub implementations for:
- Amazon KDP (Selenium-based or manual)
- Google Play Books (API-based)
- Draft2Digital (API-based)
"""

from .amazon_kdp import upload_to_kdp_node
from .draft2digital import upload_to_d2d_node
from .google_play import upload_to_google_node

__all__ = ["upload_to_kdp_node", "upload_to_google_node", "upload_to_d2d_node"]
