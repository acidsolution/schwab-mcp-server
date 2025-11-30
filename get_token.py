"""
Quick OAuth flow to get initial Schwab refresh token.

Run this script, follow the URL, authorize, and paste the redirect URL back.
"""

import base64
import json
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID")
CLIENT_SECRET = os.getenv("SCHWAB_CLIENT_SECRET")
CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL")
TOKEN_PATH = Path(os.getenv("SCHWAB_TOKEN_PATH", "~/.schwab-mcp/token.json")).expanduser()

AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


def get_auth_url() -> str:
    """Build the authorization URL."""
    return f"{AUTH_URL}?client_id={CLIENT_ID}&redirect_uri={CALLBACK_URL}"


def exchange_code_for_token(auth_code: str) -> dict:
    """Exchange authorization code for tokens."""
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    response = httpx.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": CALLBACK_URL,
        },
    )
    response.raise_for_status()
    return response.json()


def save_token(token_data: dict) -> None:
    """Save token to file."""
    import time

    token = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "expires_at": time.time() + token_data["expires_in"],
        "token_type": token_data.get("token_type", "Bearer"),
    }

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(token, f, indent=2)

    print(f"\nToken saved to: {TOKEN_PATH}")


def main():
    print("=" * 60)
    print("Schwab OAuth Token Generator")
    print("=" * 60)

    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: Missing SCHWAB_CLIENT_ID or SCHWAB_CLIENT_SECRET in .env")
        return

    auth_url = get_auth_url()

    print(f"\n1. Opening browser to authorize...\n")
    print(f"   If browser doesn't open, go to:\n   {auth_url}\n")

    webbrowser.open(auth_url)

    print("2. Log in to Schwab and authorize the app.")
    print("3. You'll be redirected to a URL (may show an error page - that's OK)")
    print("4. Copy the ENTIRE URL from your browser's address bar and paste below.\n")

    redirect_url = input("Paste the redirect URL here: ").strip()

    # Parse the authorization code from the URL
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)

    if "code" not in params:
        print("\nERROR: No authorization code found in URL.")
        print("Make sure you copied the entire URL including the ?code=... part")
        return

    auth_code = params["code"][0]
    print(f"\nExchanging code for tokens...")

    try:
        token_data = exchange_code_for_token(auth_code)
        save_token(token_data)
        print("\nSuccess! You can now run the MCP server.")
        print("\nTest with:")
        print("  npx @modelcontextprotocol/inspector venv/Scripts/python.exe -m schwab_mcp.server")
    except httpx.HTTPStatusError as e:
        print(f"\nERROR: Token exchange failed: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    main()
