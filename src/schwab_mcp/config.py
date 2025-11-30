"""Configuration management for Schwab MCP Server."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required Schwab API credentials
    schwab_client_id: str
    schwab_client_secret: str
    schwab_callback_url: str = "https://127.0.0.1:8182/callback"

    # Token storage path
    schwab_token_path: Path = Path.home() / ".schwab-mcp" / "token.json"

    # Optional settings
    log_level: str = "INFO"
    schwab_default_account: Optional[str] = None
    schwab_timeout: int = 30


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings
