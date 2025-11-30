# Schwab MCP Server

A read-only Model Context Protocol (MCP) server for Charles Schwab API, built from scratch without third-party wrappers.

## Project Goal

Build a minimal, secure MCP server that exposes Schwab account and market data to Claude, enabling:
- Portfolio analysis with real cost basis data
- Technical analysis with historical price data
- Options strategy analysis with live options chains
- Real-time quote data for execution planning

**CRITICAL: This server is READ-ONLY. No trading endpoints should be implemented.**

---

## Priority: First Cut Features

The immediate goal is to support an ongoing portfolio analysis conversation. Implement these tools first:

### Phase 1 Tools (Implement First)

| Tool | Purpose | Schwab API Endpoint |
|------|---------|---------------------|
| `get_positions` | Get all positions with cost basis, quantity, market value | `GET /trader/v1/accounts/{accountHash}?fields=positions` |
| `get_account` | Get account details (type, balances) | `GET /trader/v1/accounts/{accountHash}` |
| `get_quote` | Get real-time quote for a symbol | `GET /marketdata/v1/quotes/{symbol}` |
| `get_quotes` | Get quotes for multiple symbols | `GET /marketdata/v1/quotes?symbols=...` |
| `get_option_chain` | Get options chain for a symbol | `GET /marketdata/v1/chains` |
| `get_price_history` | Get OHLCV historical data | `GET /marketdata/v1/pricehistory` |

### Phase 2 Tools (Later)

| Tool | Purpose |
|------|---------|
| `get_transactions` | Transaction history for tax analysis |
| `get_orders` | Open/recent orders |
| `get_movers` | Market movers |

---

## Technical Requirements

### Dependencies

**Minimal - no third-party Schwab wrappers:**

```
httpx>=0.25.0         # Async HTTP client (or use aiohttp)
mcp>=1.0.0            # Model Context Protocol SDK
pydantic>=2.0.0       # Data validation and serialization
python-dotenv>=1.0.0  # Environment variable management
```

### Python Version

- Python 3.10+ required

### Authentication

The user already has:
- Schwab Developer App Key (Client ID)
- Schwab App Secret (Client Secret)  
- A working Refresh Token
- Callback URL configured

**We will implement OAuth token refresh directly against Schwab's API.**

---

## Schwab API Reference

### Base URLs

```
Authentication: https://api.schwabapi.com/v1/oauth
Trader API:     https://api.schwabapi.com/trader/v1
Market Data:    https://api.schwabapi.com/marketdata/v1
```

### OAuth 2.0 Token Refresh

The user has a working refresh token. Implement token refresh:

**Endpoint:** `POST https://api.schwabapi.com/v1/oauth/token`

**Headers:**
```
Authorization: Basic {base64(client_id:client_secret)}
Content-Type: application/x-www-form-urlencoded
```

**Body:**
```
grant_type=refresh_token&refresh_token={refresh_token}
```

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "Bearer",
  "expires_in": 1800,
  "scope": "api",
  "id_token": "string"
}
```

**Implementation Notes:**
- Access tokens expire in 30 minutes (1800 seconds)
- Refresh tokens expire in 7 days
- Store new refresh token after each refresh (it rotates)
- Implement automatic refresh when access token is expired or near expiry

---

## Project Structure

```
schwab-mcp-server/
├── src/
│   └── schwab_mcp/
│       ├── __init__.py
│       ├── server.py           # MCP server entry point
│       ├── client.py           # Schwab API HTTP client
│       ├── auth.py             # OAuth token management
│       ├── config.py           # Configuration management
│       ├── models.py           # Pydantic models for responses
│       └── tools/
│           ├── __init__.py
│           ├── account.py      # get_positions, get_account
│           ├── quotes.py       # get_quote, get_quotes
│           ├── options.py      # get_option_chain
│           └── history.py      # get_price_history
├── config/
│   └── .env.example            # Example environment file
├── tests/
│   ├── test_auth.py            # Auth tests
│   ├── test_client.py          # API client tests
│   └── test_tools.py           # Tool tests
├── pyproject.toml              # Project configuration
├── README.md                   # This file
└── claude_desktop_config.json  # Example Claude Desktop config
```

---

## Core Implementation

### 1. Configuration (`config.py`)

```python
"""Configuration management."""
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    schwab_client_id: str
    schwab_client_secret: str
    schwab_callback_url: str = "https://127.0.0.1:8182/callback"
    schwab_token_path: Path = Path.home() / ".schwab-mcp" / "token.json"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 2. Token Management (`auth.py`)

```python
"""
OAuth token management for Schwab API.
Handles token storage, refresh, and automatic renewal.
"""
import json
import base64
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import httpx

@dataclass
class Token:
    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp
    token_type: str = "Bearer"
    
    @property
    def is_expired(self) -> bool:
        # Consider expired if less than 60 seconds remaining
        return time.time() > (self.expires_at - 60)
    
    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Token":
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
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = Path(token_path)
        self._token: Optional[Token] = None
        
    def _get_basic_auth(self) -> str:
        """Generate Basic auth header value."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def load_token(self) -> Optional[Token]:
        """Load token from file."""
        if self.token_path.exists():
            with open(self.token_path) as f:
                data = json.load(f)
                self._token = Token.from_dict(data)
                return self._token
        return None
    
    def save_token(self, token: Token) -> None:
        """Save token to file with secure permissions."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w") as f:
            json.dump(token.to_dict(), f, indent=2)
        # Set file permissions to owner read/write only
        self.token_path.chmod(0o600)
        self._token = token
    
    async def refresh_token(self) -> Token:
        """Refresh the access token using the refresh token."""
        if not self._token:
            self.load_token()
        if not self._token:
            raise ValueError("No token available. Please authenticate first.")
        
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
        return new_token
    
    async def get_valid_token(self) -> Token:
        """Get a valid access token, refreshing if necessary."""
        if not self._token:
            self.load_token()
        if not self._token:
            raise ValueError("No token available. Please authenticate first.")
        
        if self._token.is_expired:
            return await self.refresh_token()
        return self._token
```

### 3. HTTP Client (`client.py`)

```python
"""
Schwab API HTTP client.
Handles all API requests with automatic token refresh.
"""
import httpx
from typing import Any, Optional
from urllib.parse import urlencode

from .auth import TokenManager

class SchwabClient:
    """Async HTTP client for Schwab API."""
    
    TRADER_BASE = "https://api.schwabapi.com/trader/v1"
    MARKET_BASE = "https://api.schwabapi.com/marketdata/v1"
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self._account_hashes: Optional[list[str]] = None
    
    async def _get_headers(self) -> dict[str, str]:
        """Get headers with valid access token."""
        token = await self.token_manager.get_valid_token()
        return {
            "Authorization": f"Bearer {token.access_token}",
            "Accept": "application/json",
        }
    
    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> Any:
        """Make an authenticated request to Schwab API."""
        headers = await self._get_headers()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()
    
    async def get(self, url: str, params: Optional[dict] = None) -> Any:
        """GET request."""
        return await self._request("GET", url, params=params)
    
    # === Account Endpoints ===
    
    async def get_account_numbers(self) -> list[dict]:
        """Get list of account numbers and hashes."""
        url = f"{self.TRADER_BASE}/accounts/accountNumbers"
        return await self.get(url)
    
    async def get_account(self, account_hash: str, fields: Optional[list[str]] = None) -> dict:
        """Get account details."""
        url = f"{self.TRADER_BASE}/accounts/{account_hash}"
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return await self.get(url, params=params if params else None)
    
    async def get_all_accounts(self, fields: Optional[list[str]] = None) -> list[dict]:
        """Get all accounts."""
        url = f"{self.TRADER_BASE}/accounts"
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return await self.get(url, params=params if params else None)
    
    # === Market Data Endpoints ===
    
    async def get_quote(self, symbol: str) -> dict:
        """Get quote for a single symbol."""
        url = f"{self.MARKET_BASE}/quotes/{symbol}"
        return await self.get(url)
    
    async def get_quotes(self, symbols: list[str]) -> dict:
        """Get quotes for multiple symbols."""
        url = f"{self.MARKET_BASE}/quotes"
        params = {"symbols": ",".join(symbols)}
        return await self.get(url, params=params)
    
    async def get_option_chain(
        self,
        symbol: str,
        contract_type: str = "ALL",
        strike_count: Optional[int] = None,
        include_underlying_quote: bool = True,
        strategy: str = "SINGLE",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> dict:
        """Get option chain for a symbol."""
        url = f"{self.MARKET_BASE}/chains"
        params = {
            "symbol": symbol,
            "contractType": contract_type,
            "includeUnderlyingQuote": str(include_underlying_quote).lower(),
            "strategy": strategy,
        }
        if strike_count:
            params["strikeCount"] = strike_count
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        return await self.get(url, params=params)
    
    async def get_price_history(
        self,
        symbol: str,
        period_type: str = "year",
        period: int = 1,
        frequency_type: str = "daily",
        frequency: int = 1,
        start_date: Optional[int] = None,  # Epoch ms
        end_date: Optional[int] = None,    # Epoch ms
        need_extended_hours: bool = False,
        need_previous_close: bool = True,
    ) -> dict:
        """Get price history for a symbol."""
        url = f"{self.MARKET_BASE}/pricehistory"
        params = {
            "symbol": symbol,
            "periodType": period_type,
            "period": period,
            "frequencyType": frequency_type,
            "frequency": frequency,
            "needExtendedHoursData": str(need_extended_hours).lower(),
            "needPreviousClose": str(need_previous_close).lower(),
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.get(url, params=params)
```

---

## Configuration

### Environment Variables

Create a `.env` file (never commit this):

```bash
# Schwab API Credentials
SCHWAB_CLIENT_ID=your_app_key_here
SCHWAB_CLIENT_SECRET=your_app_secret_here
SCHWAB_CALLBACK_URL=https://127.0.0.1:8182/callback

# Token Storage
SCHWAB_TOKEN_PATH=~/.schwab-mcp/token.json

# Optional
LOG_LEVEL=INFO
```

### Initial Token File Setup

Since the user has a working refresh token, create the initial token file manually:

```json
{
  "access_token": "paste_current_access_token_or_empty_string",
  "refresh_token": "paste_your_working_refresh_token_here",
  "expires_at": 0,
  "token_type": "Bearer"
}
```

Setting `expires_at` to 0 forces an immediate refresh on first use, which will populate a valid access token.

---

## Tool Specifications

### 1. `get_positions`

Get all positions for the account with cost basis information.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "account_id": {
      "type": "string",
      "description": "Account number or hash (optional, uses default if not provided)"
    }
  },
  "required": []
}
```

**Output Schema:**
```json
{
  "account_id": "string",
  "positions": [
    {
      "symbol": "string",
      "quantity": "number",
      "market_value": "number",
      "cost_basis": "number",
      "cost_per_share": "number",
      "gain_loss": "number",
      "gain_loss_percent": "number",
      "day_change": "number",
      "day_change_percent": "number",
      "asset_type": "string",
      "lot_details": [
        {
          "acquired_date": "string",
          "quantity": "number",
          "cost_per_share": "number",
          "cost_basis": "number",
          "term": "string"  // "SHORT_TERM" or "LONG_TERM"
        }
      ]
    }
  ]
}
```

**Implementation Notes:**
- Use `client.get_account(account_hash, fields=['positions'])` 
- Parse the `securitiesAccount.positions` array from response
- Calculate derived fields (gain/loss, percentages)
- Include lot details for tax optimization if available in response
- Handle both cash and margin account response structures

---

### 2. `get_account`

Get account information including type and balances.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "account_id": {
      "type": "string",
      "description": "Account number or hash (optional)"
    }
  },
  "required": []
}
```

**Output Schema:**
```json
{
  "account_id": "string",
  "account_type": "string",  // "INDIVIDUAL", "IRA", "ROTH_IRA", etc.
  "is_taxable": "boolean",
  "balances": {
    "cash_available": "number",
    "cash_balance": "number",
    "market_value": "number",
    "total_value": "number",
    "buying_power": "number"
  }
}
```

**Implementation Notes:**
- Use `client.get_account(account_hash)` 
- Derive `is_taxable` from account type (INDIVIDUAL, JOINT = taxable; IRA, ROTH = not taxable)
- Parse `securitiesAccount` object from response

---

### 3. `get_quote`

Get real-time quote for a single symbol.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Stock ticker symbol (e.g., 'CRM', 'AAPL')"
    }
  },
  "required": ["symbol"]
}
```

**Output Schema:**
```json
{
  "symbol": "string",
  "last_price": "number",
  "bid": "number",
  "ask": "number",
  "bid_size": "number",
  "ask_size": "number",
  "volume": "number",
  "day_high": "number",
  "day_low": "number",
  "day_open": "number",
  "prev_close": "number",
  "day_change": "number",
  "day_change_percent": "number",
  "52_week_high": "number",
  "52_week_low": "number",
  "pe_ratio": "number",
  "market_cap": "number"
}
```

**Implementation Notes:**
- Use `client.get_quote(symbol)`
- Handle both equity and ETF response structures
- Response structure: `{symbol: {assetMainType, quote: {...}, reference: {...}}}`

---

### 4. `get_quotes`

Get quotes for multiple symbols at once.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "symbols": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of ticker symbols"
    }
  },
  "required": ["symbols"]
}
```

**Output Schema:**
```json
{
  "quotes": [
    {
      // Same structure as get_quote output
    }
  ]
}
```

**Implementation Notes:**
- Use `client.get_quotes(symbols)` (batch endpoint)
- More efficient than multiple get_quote calls

---

### 5. `get_option_chain`

Get options chain for a symbol.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Underlying stock symbol"
    },
    "contract_type": {
      "type": "string",
      "enum": ["CALL", "PUT", "ALL"],
      "description": "Type of options to retrieve",
      "default": "ALL"
    },
    "strike_count": {
      "type": "integer",
      "description": "Number of strikes above and below ATM",
      "default": 10
    },
    "from_date": {
      "type": "string",
      "description": "Start date for expirations (YYYY-MM-DD)"
    },
    "to_date": {
      "type": "string",
      "description": "End date for expirations (YYYY-MM-DD)"
    },
    "expiration_month": {
      "type": "string",
      "description": "Specific expiration month (e.g., 'DEC', 'JAN')"
    }
  },
  "required": ["symbol"]
}
```

**Output Schema:**
```json
{
  "symbol": "string",
  "underlying_price": "number",
  "calls": [
    {
      "symbol": "string",
      "expiration": "string",
      "strike": "number",
      "bid": "number",
      "ask": "number",
      "last": "number",
      "volume": "number",
      "open_interest": "number",
      "implied_volatility": "number",
      "delta": "number",
      "gamma": "number",
      "theta": "number",
      "vega": "number",
      "in_the_money": "boolean",
      "days_to_expiration": "number"
    }
  ],
  "puts": [
    // Same structure as calls
  ]
}
```

**Implementation Notes:**
- Use `client.get_option_chain(symbol, ...)`
- Filter by expiration dates to reduce response size
- Include Greeks if available (delta, gamma, theta, vega)
- Sort by expiration, then by strike
- Response contains `callExpDateMap` and `putExpDateMap` nested by expiration date and strike

---

### 6. `get_price_history`

Get historical OHLCV data for technical analysis.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Stock ticker symbol"
    },
    "period_type": {
      "type": "string",
      "enum": ["day", "month", "year", "ytd"],
      "description": "Type of period",
      "default": "year"
    },
    "period": {
      "type": "integer",
      "description": "Number of periods (e.g., 1 year, 6 months)",
      "default": 1
    },
    "frequency_type": {
      "type": "string",
      "enum": ["minute", "daily", "weekly", "monthly"],
      "description": "Frequency of data points",
      "default": "daily"
    },
    "frequency": {
      "type": "integer",
      "description": "Frequency interval (e.g., every 1 day, every 5 minutes)",
      "default": 1
    },
    "start_date": {
      "type": "string",
      "description": "Start date (YYYY-MM-DD), alternative to period"
    },
    "end_date": {
      "type": "string",
      "description": "End date (YYYY-MM-DD)"
    },
    "extended_hours": {
      "type": "boolean",
      "description": "Include extended hours data",
      "default": false
    }
  },
  "required": ["symbol"]
}
```

**Output Schema:**
```json
{
  "symbol": "string",
  "candles": [
    {
      "datetime": "string",  // ISO format
      "open": "number",
      "high": "number",
      "low": "number",
      "close": "number",
      "volume": "number"
    }
  ],
  "period": "string",
  "frequency": "string"
}
```

**Implementation Notes:**
- Use `client.get_price_history()`
- Response contains `candles` array with `datetime` as epoch milliseconds
- Convert timestamps to ISO format strings for readability
- Sort chronologically (oldest first)
- Valid `periodType`: day, month, year, ytd
- Valid `frequencyType` depends on periodType:
  - day: minute
  - month: daily, weekly
  - year: daily, weekly, monthly
  - ytd: daily, weekly

---

## MCP Server Implementation

### Server Entry Point (`server.py`)

```python
"""
Schwab MCP Server - Main entry point

Exposes Schwab API data to Claude via Model Context Protocol.
READ-ONLY: No trading functionality.
"""
import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from schwab_mcp.config import settings
from schwab_mcp.auth import TokenManager
from schwab_mcp.client import SchwabClient
from schwab_mcp.tools import account, quotes, options, history

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Initialize components
token_manager = TokenManager(
    client_id=settings.schwab_client_id,
    client_secret=settings.schwab_client_secret,
    token_path=settings.schwab_token_path,
)
schwab_client = SchwabClient(token_manager)

# Initialize MCP server
server = Server("schwab-mcp")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="get_positions",
            description="Get all positions with cost basis for an account",
            inputSchema=account.GET_POSITIONS_SCHEMA
        ),
        Tool(
            name="get_account",
            description="Get account information including type and balances",
            inputSchema=account.GET_ACCOUNT_SCHEMA
        ),
        Tool(
            name="get_quote",
            description="Get real-time quote for a stock symbol",
            inputSchema=quotes.GET_QUOTE_SCHEMA
        ),
        Tool(
            name="get_quotes",
            description="Get real-time quotes for multiple symbols",
            inputSchema=quotes.GET_QUOTES_SCHEMA
        ),
        Tool(
            name="get_option_chain",
            description="Get options chain with Greeks for a symbol",
            inputSchema=options.GET_OPTION_CHAIN_SCHEMA
        ),
        Tool(
            name="get_price_history",
            description="Get historical OHLCV price data for technical analysis",
            inputSchema=history.GET_PRICE_HISTORY_SCHEMA
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool invocations."""
    logger.info(f"Tool called: {name} with args: {arguments}")
    
    handlers = {
        "get_positions": lambda args: account.get_positions(schwab_client, args),
        "get_account": lambda args: account.get_account(schwab_client, args),
        "get_quote": lambda args: quotes.get_quote(schwab_client, args),
        "get_quotes": lambda args: quotes.get_quotes(schwab_client, args),
        "get_option_chain": lambda args: options.get_option_chain(schwab_client, args),
        "get_price_history": lambda args: history.get_price_history(schwab_client, args),
    }
    
    handler = handlers.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    
    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        error_response = {
            "error": True,
            "error_type": type(e).__name__,
            "message": str(e),
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

async def main():
    """Run the MCP server."""
    logger.info("Starting Schwab MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
```

### Example Tool Implementation (`tools/account.py`)

```python
"""Account-related tools."""
from typing import Any
from schwab_mcp.client import SchwabClient

GET_POSITIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "string",
            "description": "Account hash (optional, uses first account if not provided)"
        }
    },
    "required": []
}

GET_ACCOUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "string",
            "description": "Account hash (optional, uses first account if not provided)"
        }
    },
    "required": []
}

async def get_account_hash(client: SchwabClient, account_id: str | None) -> str:
    """Get account hash, defaulting to first account if not specified."""
    if account_id:
        return account_id
    accounts = await client.get_account_numbers()
    if not accounts:
        raise ValueError("No accounts found")
    return accounts[0]["hashValue"]

async def get_positions(client: SchwabClient, args: dict) -> dict:
    """Get all positions with cost basis."""
    account_hash = await get_account_hash(client, args.get("account_id"))
    
    response = await client.get_account(account_hash, fields=["positions"])
    account_data = response.get("securitiesAccount", response)
    
    positions = []
    for pos in account_data.get("positions", []):
        instrument = pos.get("instrument", {})
        
        quantity = pos.get("longQuantity", 0) - pos.get("shortQuantity", 0)
        market_value = pos.get("marketValue", 0)
        cost_basis = pos.get("averageCostBasis", 0) * abs(quantity) if pos.get("averageCostBasis") else None
        
        position_data = {
            "symbol": instrument.get("symbol"),
            "description": instrument.get("description"),
            "asset_type": instrument.get("assetType"),
            "quantity": quantity,
            "market_value": market_value,
            "average_price": pos.get("averagePrice"),
            "cost_per_share": pos.get("averageCostBasis"),
            "cost_basis": cost_basis,
            "day_change": pos.get("currentDayProfitLoss"),
            "day_change_percent": pos.get("currentDayProfitLossPercentage"),
        }
        
        # Calculate gain/loss if we have cost basis
        if cost_basis is not None and market_value:
            position_data["gain_loss"] = market_value - cost_basis
            position_data["gain_loss_percent"] = ((market_value - cost_basis) / cost_basis * 100) if cost_basis else 0
        
        positions.append(position_data)
    
    return {
        "account_id": account_hash,
        "positions": positions
    }

async def get_account(client: SchwabClient, args: dict) -> dict:
    """Get account information."""
    account_hash = await get_account_hash(client, args.get("account_id"))
    
    response = await client.get_account(account_hash)
    account_data = response.get("securitiesAccount", response)
    
    account_type = account_data.get("type", "UNKNOWN")
    taxable_types = {"INDIVIDUAL", "JOINT", "TRUST", "CORPORATE"}
    
    balances = account_data.get("currentBalances", {})
    
    return {
        "account_id": account_hash,
        "account_type": account_type,
        "is_taxable": account_type in taxable_types,
        "balances": {
            "cash_available": balances.get("availableFunds"),
            "cash_balance": balances.get("cashBalance"),
            "market_value": balances.get("longMarketValue"),
            "total_value": balances.get("liquidationValue"),
            "buying_power": balances.get("buyingPower"),
        }
    }
```

---

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

```json
{
  "mcpServers": {
    "schwab": {
      "command": "python",
      "args": ["-m", "schwab_mcp.server"],
      "cwd": "/path/to/schwab-mcp-server",
      "env": {
        "SCHWAB_CLIENT_ID": "your_client_id",
        "SCHWAB_CLIENT_SECRET": "your_client_secret",
        "SCHWAB_CALLBACK_URL": "https://127.0.0.1:8182/callback",
        "SCHWAB_TOKEN_PATH": "/path/to/token.json"
      }
    }
  }
}
```

Alternatively, use a `.env` file and load it in the server.

---

## Security Requirements

### MUST Implement

1. **Read-only only** - No endpoints that modify account state
2. **No credential logging** - Never log tokens, secrets, or account numbers
3. **Token file permissions** - Set 600 permissions on token.json
4. **Environment variables** - Never hardcode credentials
5. **Error sanitization** - Don't expose account details in error messages

### MUST NOT Implement

1. Any order placement or modification
2. Any fund transfer functionality
3. Any account modification
4. Token storage in code
5. Credential transmission over network (except to Schwab API)

---

## Testing

### Manual Testing

```bash
# Test authentication
python -c "from schwab_mcp.auth import get_schwab_client; c = get_schwab_client(); print('Auth OK')"

# Test a tool directly
python -c "
from schwab_mcp.auth import get_schwab_client
from schwab_mcp.tools.quotes import get_quote
import asyncio

client = get_schwab_client()
result = asyncio.run(get_quote(client, {'symbol': 'AAPL'}))
print(result)
"
```

### With MCP Inspector

```bash
npx @modelcontextprotocol/inspector python -m schwab_mcp.server
```

---

## Error Handling

All tools should handle these cases:

1. **Authentication failure** - Token expired, refresh failed
2. **Rate limiting** - Schwab API limits (120 requests/minute)
3. **Invalid symbol** - Symbol not found
4. **Market closed** - Some data unavailable outside hours
5. **Network errors** - Timeout, connection refused

Return structured errors:

```json
{
  "error": true,
  "error_type": "AUTH_FAILED",
  "message": "Token refresh failed. Please re-authenticate.",
  "details": {}
}
```

---

## Usage Examples

Once running, Claude can use the tools like this:

**Get portfolio positions:**
> "What are my current positions and their cost basis?"

Claude calls: `get_positions({})`

**Analyze a stock:**
> "Give me technical analysis on CRM"

Claude calls: `get_price_history({"symbol": "CRM", "period_type": "year", "period": 1})`

**Options analysis:**
> "What covered calls could I sell on my CRM position?"

Claude calls: `get_option_chain({"symbol": "CRM", "contract_type": "CALL", "to_date": "2026-01-17"})`

---

## Development Workflow

1. Clone/create the project structure
2. Set up virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -e ".[dev]"`
4. Configure credentials in `.env`
5. Test authentication: `python -c "from schwab_mcp.auth import get_schwab_client; get_schwab_client()"`
6. Run with MCP inspector: `npx @modelcontextprotocol/inspector python -m schwab_mcp.server`
7. Add to Claude Desktop config
8. Restart Claude Desktop

---

## References

- [Schwab Developer Portal](https://developer.schwab.com/)
- [Schwab API Documentation](https://developer.schwab.com/products/trader-api--individual/details/documentation)
- [Schwab Market Data API](https://developer.schwab.com/products/trader-api--individual/details/documentation/Market%20Data%20Production)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [httpx Documentation](https://www.python-httpx.org/)

---

## License

MIT - Use at your own risk. Not affiliated with Charles Schwab.

---

## Immediate Next Steps for Claude Code

1. **Create project structure** as specified above
2. **Implement `config.py`** - load settings from environment
3. **Implement `auth.py`** - TokenManager class with refresh logic
4. **Implement `client.py`** - SchwabClient with all API methods
5. **Implement Phase 1 tools** in order: `get_account` → `get_positions` → `get_quote` → `get_price_history` → `get_option_chain`
6. **Wire up `server.py`** with all tools
7. **Test with MCP inspector**
8. **Configure Claude Desktop**

The user has a working refresh token. Create initial token.json with `expires_at: 0` to force refresh on first use.
