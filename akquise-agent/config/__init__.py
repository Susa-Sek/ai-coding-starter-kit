"""
Configuration package for Akquise Agent.
"""

from .settings import (
    Settings,
    ScraperSettings,
    ProxySettings,
    DatabaseSettings,
    EmailSettings,
    FollowUpSettings,
    ExportSettings,
    LoggingSettings,
    settings,
)

__all__ = [
    "Settings",
    "ScraperSettings",
    "ProxySettings",
    "DatabaseSettings",
    "EmailSettings",
    "FollowUpSettings",
    "ExportSettings",
    "LoggingSettings",
    "settings",
]