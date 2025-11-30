"""Options-related tools for Schwab MCP Server."""

from typing import Any, Optional

from ..client import SchwabClient

# Schema for get_option_chain tool
GET_OPTION_CHAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Underlying stock symbol",
        },
        "contract_type": {
            "type": "string",
            "enum": ["CALL", "PUT", "ALL"],
            "description": "Type of options to retrieve",
            "default": "ALL",
        },
        "strike_count": {
            "type": "integer",
            "description": "Number of strikes above and below ATM (default: all strikes)",
        },
        "from_date": {
            "type": "string",
            "description": "Start date for expirations (YYYY-MM-DD)",
        },
        "to_date": {
            "type": "string",
            "description": "End date for expirations (YYYY-MM-DD)",
        },
    },
    "required": ["symbol"],
}


def _parse_option_contract(strike: str, contract_data: list) -> Optional[dict[str, Any]]:
    """
    Parse a single option contract from Schwab API response.

    Args:
        strike: Strike price as string
        contract_data: List of contract data (usually just one element)

    Returns:
        Parsed option contract dict or None
    """
    if not contract_data:
        return None

    opt = contract_data[0]  # First contract at this strike

    return {
        "symbol": opt.get("symbol"),
        "description": opt.get("description"),
        "strike": float(strike),
        "expiration": opt.get("expirationDate"),
        "days_to_expiration": opt.get("daysToExpiration"),
        "bid": opt.get("bid"),
        "ask": opt.get("ask"),
        "last": opt.get("last"),
        "mark": opt.get("mark"),
        "volume": opt.get("totalVolume"),
        "open_interest": opt.get("openInterest"),
        "implied_volatility": opt.get("volatility"),
        "delta": opt.get("delta"),
        "gamma": opt.get("gamma"),
        "theta": opt.get("theta"),
        "vega": opt.get("vega"),
        "rho": opt.get("rho"),
        "in_the_money": opt.get("inTheMoney"),
        "intrinsic_value": opt.get("intrinsicValue"),
        "extrinsic_value": opt.get("extrinsicValue"),
        "time_value": opt.get("timeValue"),
    }


def _parse_option_map(exp_date_map: dict) -> list[dict[str, Any]]:
    """
    Parse option expiration date map from Schwab API.

    Args:
        exp_date_map: Dict of expiration dates -> strikes -> contracts

    Returns:
        Flat list of parsed option contracts
    """
    options = []

    for exp_date, strikes in exp_date_map.items():
        for strike, contracts in strikes.items():
            parsed = _parse_option_contract(strike, contracts)
            if parsed:
                options.append(parsed)

    # Sort by expiration, then by strike
    options.sort(key=lambda x: (x.get("expiration", ""), x.get("strike", 0)))
    return options


async def get_option_chain(client: SchwabClient, args: dict) -> dict[str, Any]:
    """
    Get options chain for a symbol with Greeks.

    Args:
        client: SchwabClient instance
        args: Tool arguments with symbol and optional filters

    Returns:
        Dict with underlying info, calls, and puts
    """
    symbol = args["symbol"].upper()
    contract_type = args.get("contract_type", "ALL")
    strike_count = args.get("strike_count")
    from_date = args.get("from_date")
    to_date = args.get("to_date")

    response = await client.get_option_chain(
        symbol=symbol,
        contract_type=contract_type,
        strike_count=strike_count,
        from_date=from_date,
        to_date=to_date,
    )

    # Get underlying quote if available
    underlying = response.get("underlying", {})
    underlying_price = underlying.get("last") or underlying.get("mark")

    # Parse calls and puts
    calls = []
    puts = []

    call_map = response.get("callExpDateMap", {})
    put_map = response.get("putExpDateMap", {})

    if contract_type in ("CALL", "ALL"):
        calls = _parse_option_map(call_map)

    if contract_type in ("PUT", "ALL"):
        puts = _parse_option_map(put_map)

    return {
        "symbol": symbol,
        "underlying_price": underlying_price,
        "underlying": {
            "last": underlying.get("last"),
            "bid": underlying.get("bid"),
            "ask": underlying.get("ask"),
            "change": underlying.get("change"),
            "percent_change": underlying.get("percentChange"),
            "volume": underlying.get("totalVolume"),
        },
        "status": response.get("status"),
        "is_delayed": response.get("isDelayed"),
        "number_of_contracts": response.get("numberOfContracts"),
        "calls": calls,
        "puts": puts,
    }
