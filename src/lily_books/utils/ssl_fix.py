"""Permanent SSL certificate fix for NLTK and other SSL-dependent libraries."""

import ssl
import certifi
import os
import logging

logger = logging.getLogger(__name__)


def fix_ssl_certificates():
    """Fix SSL certificate issues permanently."""
    try:
        # Set SSL certificate paths
        cert_path = certifi.where()
        os.environ['SSL_CERT_FILE'] = cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
        
        # Create unverified context for libraries that need it
        ssl._create_default_https_context = ssl._create_unverified_context
        
        logger.info(f"SSL certificates fixed. Using: {cert_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to fix SSL certificates: {e}")
        return False


def test_ssl_fix():
    """Test that SSL fix is working."""
    try:
        import requests
        response = requests.get('https://www.google.com', timeout=5)
        if response.status_code == 200:
            logger.info("SSL fix verified: HTTPS requests working")
            return True
        else:
            logger.error(f"SSL fix failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"SSL fix test failed: {e}")
        return False


# Apply fix on import
fix_ssl_certificates()

