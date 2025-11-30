"""
Schwab MCP Server

A read-only Model Context Protocol (MCP) server for Charles Schwab API.
Enables Claude to analyze portfolios, quotes, options, and price history.
"""

__version__ = "0.1.0"

from .auth import Token, TokenManager
from .client import SchwabClient
from .config import Settings, settings

__all__ = [
    "Token",
    "TokenManager",
    "SchwabClient",
    "Settings",
    "settings",
]
