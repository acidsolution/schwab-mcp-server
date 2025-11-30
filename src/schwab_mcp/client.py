"""
Schwab API HTTP client.

Handles all API requests with automatic token refresh.
READ-ONLY: No trading functionality.
"""

import logging
from typing import Any, Optional

import httpx

from .auth import TokenManager

logger = logging.getLogger(__name__)


class SchwabClient:
    """Async HTTP client for Schwab API."""

    TRADER_BASE = "https://api.schwabapi.com/trader/v1"
    MARKET_BASE = "https://api.schwabapi.com/marketdata/v1"

    def __init__(self, token_manager: TokenManager, timeout: int = 30):
        """
        Initialize SchwabClient.

        Args:
            token_manager: TokenManager instance for authentication
            timeout: Request timeout in seconds
        """
        self.token_manager = token_manager
        self.timeout = timeout
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
        """
        Make an authenticated request to Schwab API.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            params: Optional query parameters
            json_data: Optional JSON body data

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        headers = await self._get_headers()

        async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
            )

            # Log non-sensitive request info
            logger.debug(f"{method} {url} -> {response.status_code}")

            response.raise_for_status()
            return response.json()

    async def get(self, url: str, params: Optional[dict] = None) -> Any:
        """Make GET request."""
        return await self._request("GET", url, params=params)

    # ==========================================================================
    # Account Endpoints (Trader API)
    # ==========================================================================

    async def get_account_numbers(self) -> list[dict]:
        """
        Get list of account numbers and hashes.

        Returns:
            List of dicts with 'accountNumber' and 'hashValue' keys
        """
        url = f"{self.TRADER_BASE}/accounts/accountNumbers"
        return await self.get(url)

    async def get_account(
        self, account_hash: str, fields: Optional[list[str]] = None
    ) -> dict:
        """
        Get account details.

        Args:
            account_hash: Account hash from get_account_numbers
            fields: Optional fields to include (e.g., ['positions'])

        Returns:
            Account data including balances and optionally positions
        """
        url = f"{self.TRADER_BASE}/accounts/{account_hash}"
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return await self.get(url, params=params if params else None)

    async def get_all_accounts(self, fields: Optional[list[str]] = None) -> list[dict]:
        """
        Get all accounts.

        Args:
            fields: Optional fields to include

        Returns:
            List of account data
        """
        url = f"{self.TRADER_BASE}/accounts"
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return await self.get(url, params=params if params else None)

    # ==========================================================================
    # Market Data Endpoints
    # ==========================================================================

    async def get_quote(self, symbol: str) -> dict:
        """
        Get quote for a single symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Quote data including price, bid/ask, volume
        """
        # Use the batch quotes endpoint with single symbol
        url = f"{self.MARKET_BASE}/quotes"
        params = {"symbols": symbol.upper()}
        return await self.get(url, params=params)

    async def get_quotes(self, symbols: list[str]) -> dict:
        """
        Get quotes for multiple symbols.

        Args:
            symbols: List of ticker symbols

        Returns:
            Dict of symbol -> quote data
        """
        url = f"{self.MARKET_BASE}/quotes"
        params = {"symbols": ",".join(s.upper() for s in symbols)}
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
        """
        Get option chain for a symbol.

        Args:
            symbol: Underlying stock symbol
            contract_type: CALL, PUT, or ALL
            strike_count: Number of strikes above/below ATM
            include_underlying_quote: Include underlying stock quote
            strategy: Options strategy (SINGLE, etc.)
            from_date: Start date for expirations (YYYY-MM-DD)
            to_date: End date for expirations (YYYY-MM-DD)

        Returns:
            Option chain data with calls and puts
        """
        url = f"{self.MARKET_BASE}/chains"
        params = {
            "symbol": symbol.upper(),
            "contractType": contract_type,
            "includeUnderlyingQuote": str(include_underlying_quote).lower(),
            "strategy": strategy,
        }
        if strike_count is not None:
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
        end_date: Optional[int] = None,  # Epoch ms
        need_extended_hours: bool = False,
        need_previous_close: bool = True,
    ) -> dict:
        """
        Get price history for a symbol.

        Args:
            symbol: Stock ticker symbol
            period_type: day, month, year, or ytd
            period: Number of periods
            frequency_type: minute, daily, weekly, or monthly
            frequency: Frequency interval
            start_date: Start date as epoch milliseconds
            end_date: End date as epoch milliseconds
            need_extended_hours: Include extended hours data
            need_previous_close: Include previous close price

        Returns:
            Price history with OHLCV candles
        """
        url = f"{self.MARKET_BASE}/pricehistory"
        params = {
            "symbol": symbol.upper(),
            "periodType": period_type,
            "period": period,
            "frequencyType": frequency_type,
            "frequency": frequency,
            "needExtendedHoursData": str(need_extended_hours).lower(),
            "needPreviousClose": str(need_previous_close).lower(),
        }
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date

        return await self.get(url, params=params)
