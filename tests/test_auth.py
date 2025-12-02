"""Tests for the auth module."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from schwab_mcp.auth import Token, TokenManager


class TestToken:
    """Tests for the Token dataclass."""

    def test_token_creation(self):
        """Test creating a token with all fields."""
        token = Token(
            access_token="test_access",
            refresh_token="test_refresh",
            expires_at=time.time() + 3600,
            token_type="Bearer",
        )
        assert token.access_token == "test_access"
        assert token.refresh_token == "test_refresh"
        assert token.token_type == "Bearer"

    def test_token_is_expired_false(self):
        """Test is_expired returns False for valid token."""
        token = Token(
            access_token="test",
            refresh_token="test",
            expires_at=time.time() + 3600,  # Expires in 1 hour
        )
        assert token.is_expired is False

    def test_token_is_expired_true(self):
        """Test is_expired returns True for expired token."""
        token = Token(
            access_token="test",
            refresh_token="test",
            expires_at=time.time() - 100,  # Expired 100 seconds ago
        )
        assert token.is_expired is True

    def test_token_is_expired_within_buffer(self):
        """Test is_expired returns True when within 60s buffer."""
        token = Token(
            access_token="test",
            refresh_token="test",
            expires_at=time.time() + 30,  # Expires in 30 seconds (within buffer)
        )
        assert token.is_expired is True

    def test_token_to_dict(self):
        """Test converting token to dictionary."""
        expires_at = time.time() + 3600
        token = Token(
            access_token="access123",
            refresh_token="refresh456",
            expires_at=expires_at,
            token_type="Bearer",
        )
        data = token.to_dict()
        assert data == {
            "access_token": "access123",
            "refresh_token": "refresh456",
            "expires_at": expires_at,
            "token_type": "Bearer",
        }

    def test_token_from_dict(self):
        """Test creating token from dictionary."""
        expires_at = time.time() + 3600
        data = {
            "access_token": "access123",
            "refresh_token": "refresh456",
            "expires_at": expires_at,
            "token_type": "Bearer",
        }
        token = Token.from_dict(data)
        assert token.access_token == "access123"
        assert token.refresh_token == "refresh456"
        assert token.expires_at == expires_at
        assert token.token_type == "Bearer"

    def test_token_from_dict_default_token_type(self):
        """Test token_type defaults to Bearer if not in dict."""
        data = {
            "access_token": "access123",
            "refresh_token": "refresh456",
            "expires_at": time.time() + 3600,
        }
        token = Token.from_dict(data)
        assert token.token_type == "Bearer"


class TestTokenManager:
    """Tests for the TokenManager class."""

    def test_token_manager_init(self):
        """Test TokenManager initialization."""
        tm = TokenManager(
            client_id="test_id",
            client_secret="test_secret",
            token_path=Path("/tmp/test_token.json"),
        )
        assert tm.client_id == "test_id"
        assert tm.client_secret == "test_secret"
        assert tm.token_path == Path("/tmp/test_token.json")

    def test_get_basic_auth(self):
        """Test Basic auth header generation."""
        import base64

        tm = TokenManager(
            client_id="my_client_id",
            client_secret="my_client_secret",
            token_path=Path("/tmp/test.json"),
        )
        auth = tm._get_basic_auth()

        # Verify the format
        assert auth.startswith("Basic ")

        # Decode and verify
        encoded = auth.replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "my_client_id:my_client_secret"

    def test_load_token_file_not_exists(self):
        """Test load_token returns None when file doesn't exist."""
        tm = TokenManager(
            client_id="test",
            client_secret="test",
            token_path=Path("/nonexistent/path/token.json"),
        )
        result = tm.load_token()
        assert result is None

    def test_load_and_save_token(self):
        """Test saving and loading a token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = Path(tmpdir) / "token.json"
            tm = TokenManager(
                client_id="test",
                client_secret="test",
                token_path=token_path,
            )

            # Create and save a token
            expires_at = time.time() + 3600
            token = Token(
                access_token="saved_access",
                refresh_token="saved_refresh",
                expires_at=expires_at,
            )
            tm.save_token(token)

            # Verify file exists
            assert token_path.exists()

            # Load token in new manager instance
            tm2 = TokenManager(
                client_id="test",
                client_secret="test",
                token_path=token_path,
            )
            loaded = tm2.load_token()

            assert loaded is not None
            assert loaded.access_token == "saved_access"
            assert loaded.refresh_token == "saved_refresh"
            assert loaded.expires_at == expires_at

    def test_load_token_invalid_json(self):
        """Test load_token handles invalid JSON gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = Path(tmpdir) / "token.json"
            token_path.write_text("not valid json")

            tm = TokenManager(
                client_id="test",
                client_secret="test",
                token_path=token_path,
            )
            result = tm.load_token()
            assert result is None

    def test_load_token_missing_keys(self):
        """Test load_token handles missing required keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = Path(tmpdir) / "token.json"
            token_path.write_text(json.dumps({"access_token": "only_access"}))

            tm = TokenManager(
                client_id="test",
                client_secret="test",
                token_path=token_path,
            )
            result = tm.load_token()
            assert result is None
