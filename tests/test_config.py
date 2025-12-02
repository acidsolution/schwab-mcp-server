"""Tests for the config module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from schwab_mcp.config import Settings, get_settings


class TestSettings:
    """Tests for the Settings class."""

    def test_settings_required_fields(self):
        """Test that required fields are enforced."""
        # Without setting env vars, this should fail
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):  # ValidationError
                Settings()

    def test_settings_with_env_vars(self):
        """Test settings load from environment variables."""
        env = {
            "SCHWAB_CLIENT_ID": "test_client_id",
            "SCHWAB_CLIENT_SECRET": "test_client_secret",
            "SCHWAB_CALLBACK_URL": "https://localhost:8000/callback",
            "SCHWAB_TOKEN_PATH": "/tmp/token.json",
            "LOG_LEVEL": "DEBUG",
            "SCHWAB_TIMEOUT": "60",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

            assert settings.schwab_client_id == "test_client_id"
            assert settings.schwab_client_secret == "test_client_secret"
            assert settings.schwab_callback_url == "https://localhost:8000/callback"
            assert settings.schwab_token_path == Path("/tmp/token.json")
            assert settings.log_level == "DEBUG"
            assert settings.schwab_timeout == 60

    def test_settings_defaults(self):
        """Test that default values are applied."""
        env = {
            "SCHWAB_CLIENT_ID": "test_id",
            "SCHWAB_CLIENT_SECRET": "test_secret",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

            assert settings.schwab_callback_url == "https://127.0.0.1:8182/callback"
            assert settings.log_level == "INFO"
            assert settings.schwab_timeout == 30
            assert settings.schwab_default_account is None

    def test_settings_token_path_default(self):
        """Test default token path is in home directory."""
        env = {
            "SCHWAB_CLIENT_ID": "test_id",
            "SCHWAB_CLIENT_SECRET": "test_secret",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

            expected = Path.home() / ".schwab-mcp" / "token.json"
            assert settings.schwab_token_path == expected

    def test_get_settings_function(self):
        """Test the get_settings convenience function."""
        env = {
            "SCHWAB_CLIENT_ID": "test_id",
            "SCHWAB_CLIENT_SECRET": "test_secret",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = get_settings()
            assert isinstance(settings, Settings)
            assert settings.schwab_client_id == "test_id"
