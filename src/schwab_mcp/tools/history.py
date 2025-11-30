"""Price history tools for Schwab MCP Server."""

from datetime import datetime
from typing import Any, Optional

from ..client import SchwabClient

# Schema for get_price_history tool
GET_PRICE_HISTORY_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Stock ticker symbol",
        },
        "period_type": {
            "type": "string",
            "enum": ["day", "month", "year", "ytd"],
            "description": "Type of period (default: year)",
            "default": "year",
        },
        "period": {
            "type": "integer",
            "description": "Number of periods (default: 1)",
            "default": 1,
        },
        "frequency_type": {
            "type": "string",
            "enum": ["minute", "daily", "weekly", "monthly"],
            "description": "Frequency of data points (default: daily)",
            "default": "daily",
        },
        "frequency": {
            "type": "integer",
            "description": "Frequency interval (default: 1)",
            "default": 1,
        },
        "start_date": {
            "type": "string",
            "description": "Start date (YYYY-MM-DD), alternative to period",
        },
        "end_date": {
            "type": "string",
            "description": "End date (YYYY-MM-DD)",
        },
        "extended_hours": {
            "type": "boolean",
            "description": "Include extended hours data (default: false)",
            "default": False,
        },
    },
    "required": ["symbol"],
}


def _date_to_epoch_ms(date_str: str) -> int:
    """
    Convert date string to epoch milliseconds.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Epoch time in milliseconds
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp() * 1000)


def _epoch_ms_to_iso(epoch_ms: int) -> str:
    """
    Convert epoch milliseconds to ISO format string.

    Args:
        epoch_ms: Epoch time in milliseconds

    Returns:
        ISO format date string
    """
    dt = datetime.fromtimestamp(epoch_ms / 1000)
    return dt.isoformat()


def _parse_candle(candle: dict) -> dict[str, Any]:
    """
    Parse a single candle from Schwab API response.

    Args:
        candle: Raw candle data

    Returns:
        Parsed candle dict with ISO datetime
    """
    return {
        "datetime": _epoch_ms_to_iso(candle["datetime"]),
        "open": candle.get("open"),
        "high": candle.get("high"),
        "low": candle.get("low"),
        "close": candle.get("close"),
        "volume": candle.get("volume"),
    }


async def get_price_history(client: SchwabClient, args: dict) -> dict[str, Any]:
    """
    Get historical OHLCV price data for technical analysis.

    Args:
        client: SchwabClient instance
        args: Tool arguments with symbol and optional date/period params

    Returns:
        Dict with symbol, metadata, and candles list
    """
    symbol = args["symbol"].upper()
    period_type = args.get("period_type", "year")
    period = args.get("period", 1)
    frequency_type = args.get("frequency_type", "daily")
    frequency = args.get("frequency", 1)
    extended_hours = args.get("extended_hours", False)

    # Convert date strings to epoch ms if provided
    start_date: Optional[int] = None
    end_date: Optional[int] = None

    if args.get("start_date"):
        start_date = _date_to_epoch_ms(args["start_date"])
    if args.get("end_date"):
        end_date = _date_to_epoch_ms(args["end_date"])

    response = await client.get_price_history(
        symbol=symbol,
        period_type=period_type,
        period=period,
        frequency_type=frequency_type,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        need_extended_hours=extended_hours,
    )

    # Parse candles and convert timestamps
    raw_candles = response.get("candles", [])
    candles = [_parse_candle(c) for c in raw_candles]

    # Sort chronologically (oldest first)
    candles.sort(key=lambda x: x["datetime"])

    return {
        "symbol": symbol,
        "period_type": period_type,
        "period": period,
        "frequency_type": frequency_type,
        "frequency": frequency,
        "previous_close": response.get("previousClose"),
        "previous_close_date": response.get("previousCloseDate"),
        "candle_count": len(candles),
        "candles": candles,
    }
