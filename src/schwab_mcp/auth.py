"""
OAuth token management for Schwab API.

Handles token storage, refresh, and automatic renewal.
"""

import base64
import json
import logging
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Token:
    """OAuth token data."""

    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp
    token_type: str = "Bearer"

    @property
    def is_expired(self) -> bool:
        """Check if token is expired or near expiry (60s buffer)."""
        return time.time() > (self.expires_at - 60)

    def to_dict(self) -> dict:
        """Convert token to dictionary for storage."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Token":
        """Create token from dictionary."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data["expires_at"],
            token_type=data.get("token_type", "Bearer"),
        )


class TokenManager:
    """Manages OAuth tokens with automatic refresh."""

    OAUTH_URL = "https://api.schwabapi.com/v1/oauth/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_path: Path,
    ):
        """
        Initialize TokenManager.

        Args:
            client_id: Schwab API client ID
            client_secret: Schwab API client secret
            token_path: Path to store token JSON file
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = Path(token_path).expanduser()
        self._token: Optional[Token] = None

    def _get_basic_auth(self) -> str:
        """Generate Basic auth header value."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def load_token(self) -> Optional[Token]:
        """Load token from file."""
        if self.token_path.exists():
            try:
                with open(self.token_path) as f:
                    data = json.load(f)
                    self._token = Token.from_dict(data)
                    logger.debug("Token loaded from file")
                    return self._token
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to load token: {e}")
                return None
        return None

    def save_token(self, token: Token) -> None:
        """Save token to file with secure permissions."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.token_path, "w") as f:
            json.dump(token.to_dict(), f, indent=2)

        # Set file permissions to owner read/write only (Unix-like systems)
        try:
            os.chmod(self.token_path, stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, AttributeError):
            # Windows doesn't support chmod the same way
            pass

        self._token = token
        logger.debug("Token saved to file")

    async def refresh_token(self) -> Token:
        """
        Refresh the access token using the refresh token.

        Returns:
            New Token with fresh access and refresh tokens

        Raises:
            ValueError: If no token is available
            httpx.HTTPStatusError: If refresh request fails
        """
        if not self._token:
            self.load_token()
        if not self._token:
            raise ValueError("No token available. Please authenticate first.")

        logger.info("Refreshing access token...")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_URL,
                headers={
                    "Authorization": self._get_basic_auth(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._token.refresh_token,
                },
            )
            response.raise_for_status()
            data = response.json()

        new_token = Token(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + data["expires_in"],
            token_type=data.get("token_type", "Bearer"),
        )

        self.save_token(new_token)
        logger.info("Token refreshed successfully")
        return new_token

    async def get_valid_token(self) -> Token:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid Token that can be used for API requests

        Raises:
            ValueError: If no token is available
        """
        if not self._token:
            self.load_token()
        if not self._token:
            raise ValueError("No token available. Please authenticate first.")

        if self._token.is_expired:
            logger.debug("Token expired, refreshing...")
            return await self.refresh_token()

        return self._token
