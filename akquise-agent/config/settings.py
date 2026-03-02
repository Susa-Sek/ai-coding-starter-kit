"""
Configuration settings for Akquise Agent.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ScraperSettings:
    """Settings for browser scraping."""
    headless: bool = True
    timeout: int = 30000  # milliseconds
    rate_limit_delay: float = 2.0  # seconds between requests
    max_retries: int = 3
    retry_backoff: float = 2.0  # exponential backoff multiplier
    screenshot_on_fail: bool = True

    # User agent rotation
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ])


@dataclass
class ProxySettings:
    """Settings for proxy rotation."""
    enabled: bool = False
    proxy_file: str = "config/proxies.txt"
    rotation_mode: str = "round_robin"  # round_robin, random, least_used
    max_failures: int = 3  # max failures before proxy is removed
    test_url: str = "https://httpbin.org/ip"


@dataclass
class DatabaseSettings:
    """Settings for SQLite database."""
    path: str = "data/contacts.db"
    pool_size: int = 5


@dataclass
class EmailSettings:
    """Settings for email generation."""
    template_dir: str = "templates/emails"
    default_language: str = "de"
    max_drafts_per_run: int = 50


@dataclass
class FollowUpSettings:
    """Settings for follow-up automation."""
    first_reminder_days: int = 7
    second_reminder_days: int = 14
    max_reminders: int = 2


@dataclass
class ExportSettings:
    """Settings for data export."""
    output_dir: str = "data/exports"
    csv_delimiter: str = ";"
    include_headers: bool = True


@dataclass
class LoggingSettings:
    """Settings for logging."""
    level: str = "INFO"
    file: str = "logs/akquise.log"
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class Settings:
    """Main application settings."""
    app_name: str = "Akquise Agent"
    version: str = "0.1.0"
    debug: bool = False

    # Sub-settings
    scraper: ScraperSettings = field(default_factory=ScraperSettings)
    proxy: ProxySettings = field(default_factory=ProxySettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    email: EmailSettings = field(default_factory=EmailSettings)
    follow_up: FollowUpSettings = field(default_factory=FollowUpSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    # Target configuration
    target_location: str = "Heilbronn"
    target_radius_km: int = 50
    min_units: int = 50
    max_units: int = 500
    max_employees: int = 100

    # Google Drive integration
    google_drive_enabled: bool = False
    google_drive_folder_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'Settings':
        """Create settings from environment variables."""
        settings = cls()

        # Override from environment
        settings.debug = os.getenv("DEBUG", "false").lower() == "true"
        settings.scraper.headless = os.getenv("HEADLESS", "true").lower() == "true"
        settings.scraper.timeout = int(os.getenv("SCRAPER_TIMEOUT", "30000"))
        settings.proxy.enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
        settings.database.path = os.getenv("DATABASE_PATH", "data/contacts.db")
        settings.target_location = os.getenv("TARGET_LOCATION", "Heilbronn")
        settings.google_drive_enabled = os.getenv("GOOGLE_DRIVE_ENABLED", "false").lower() == "true"
        settings.google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

        return settings

    def ensure_directories(self):
        """Create necessary directories."""
        Path(self.database.path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.export.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.logging.file).parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings.from_env()