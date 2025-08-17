"""
TrustNoCorpo - Cryptographic PDF Tracking System
==========================================

A sophisticated system for embedding cryptographic tracking information
into LaTeX-generated PDFs with user-level encryption and audit trails.

Version: 1.0.1
Author: trustnocorpo Security Team
License: MIT
"""

__version__ = "1.0.1"
__author__ = "TrustNoCorpo Security Team"
__license__ = "MIT"

from .core import trustnocorpo
from .keys import KeyManager
from .protector import PDFProtector
from .logger import BuildLogger

__all__ = [
    'trustnocorpo',
    'KeyManager', 
    'PDFProtector',
    'BuildLogger',
]
