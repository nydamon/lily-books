"""Retailer upload integrations for distribution.

PRIMARY: PublishDrive (manual upload, Selenium automation planned)
LEGACY/BACKUP: Amazon KDP, Google Play Books, Draft2Digital
"""

from .publishdrive import upload_to_publishdrive_node  # PRIMARY ⭐
from .amazon_kdp import upload_to_kdp_node  # LEGACY/BACKUP
from .draft2digital import upload_to_d2d_node  # LEGACY/BACKUP
from .google_play import upload_to_google_node  # LEGACY/BACKUP

__all__ = [
    "upload_to_publishdrive_node",  # Recommended
    "upload_to_kdp_node",  # Backup
    "upload_to_google_node",  # Backup
    "upload_to_d2d_node",  # Backup
]
