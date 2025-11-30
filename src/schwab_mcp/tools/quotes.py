"""Quote-related tools for Schwab MCP Server."""

from typing import Any

from ..client import SchwabClient

# Schema for get_quote tool
GET_QUOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL', 'CRM')",
        }
    },
    "required": ["symbol"],
}

# Schema for get_quotes tool
GET_QUOTES_SCHEMA = {
    "type": "object",
    "properties": {
        "symbols": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of ticker symbols",
        }
    },
    "required": ["symbols"],
}


def _parse_quote(symbol: str, data: dict) -> dict[str, Any]:
    """
    Parse quote data from Schwab API response.

    Args:
        symbol: Stock ticker symbol
        data: Raw quote data from API

    Returns:
        Parsed quote dict
    """
    quote = data.get("quote", {})
    reference = data.get("reference", {})

    return {
        "symbol": symbol,
        "asset_type": data.get("assetMainType"),
        "last_price": quote.get("lastPrice"),
        "bid": quote.get("bidPrice"),
        "ask": quote.get("askPrice"),
        "bid_size": quote.get("bidSize"),
        "ask_size": quote.get("askSize"),
        "volume": quote.get("totalVolume"),
        "day_high": quote.get("highPrice"),
        "day_low": quote.get("lowPrice"),
        "day_open": quote.get("openPrice"),
        "prev_close": quote.get("closePrice"),
        "day_change": quote.get("netChange"),
        "day_change_percent": quote.get("netPercentChange"),
        "52_week_high": quote.get("52WeekHigh"),
        "52_week_low": quote.get("52WeekLow"),
        "pe_ratio": quote.get("peRatio"),
        "div_yield": quote.get("divYield"),
        "market_cap": reference.get("marketCap"),
        "exchange": reference.get("exchange"),
        "description": reference.get("description"),
    }


async def get_quote(client: SchwabClient, args: dict) -> dict[str, Any]:
    """
    Get real-time quote for a single symbol.

    Args:
        client: SchwabClient instance
        args: Tool arguments with 'symbol'

    Returns:
        Quote data dict
    """
    symbol = args["symbol"].upper()
    response = await client.get_quote(symbol)

    # Response structure: {SYMBOL: {assetMainType, quote, reference}}
    data = response.get(symbol, response)
    return _parse_quote(symbol, data)


async def get_quotes(client: SchwabClient, args: dict) -> dict[str, Any]:
    """
    Get real-time quotes for multiple symbols.

    Args:
        client: SchwabClient instance
        args: Tool arguments with 'symbols' list

    Returns:
        Dict with quotes list
    """
    symbols = [s.upper() for s in args["symbols"]]
    response = await client.get_quotes(symbols)

    quotes = []
    for symbol in symbols:
        if symbol in response:
            quotes.append(_parse_quote(symbol, response[symbol]))
        else:
            # Symbol not found
            quotes.append({"symbol": symbol, "error": "Symbol not found"})

    return {"quotes": quotes}
