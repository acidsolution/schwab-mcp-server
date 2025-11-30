"""Account-related tools for Schwab MCP Server."""

from typing import Any, Optional

from ..client import SchwabClient

# Schema for get_positions tool
GET_POSITIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "string",
            "description": "Account hash (optional, uses first account if not provided)",
        }
    },
    "required": [],
}

# Schema for get_account tool
GET_ACCOUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "string",
            "description": "Account hash (optional, uses first account if not provided)",
        }
    },
    "required": [],
}


async def get_account_hash(client: SchwabClient, account_id: Optional[str]) -> str:
    """
    Get account hash, defaulting to first account if not specified.

    Args:
        client: SchwabClient instance
        account_id: Optional account hash

    Returns:
        Account hash string

    Raises:
        ValueError: If no accounts found
    """
    if account_id:
        return account_id

    accounts = await client.get_account_numbers()
    if not accounts:
        raise ValueError("No accounts found")
    return accounts[0]["hashValue"]


async def get_positions(client: SchwabClient, args: dict) -> dict[str, Any]:
    """
    Get all positions with cost basis for an account.

    Args:
        client: SchwabClient instance
        args: Tool arguments (optional account_id)

    Returns:
        Dict with account_id and positions list
    """
    account_hash = await get_account_hash(client, args.get("account_id"))

    response = await client.get_account(account_hash, fields=["positions"])
    account_data = response.get("securitiesAccount", response)

    positions = []
    for pos in account_data.get("positions", []):
        instrument = pos.get("instrument", {})

        # Calculate quantity (long - short)
        long_qty = pos.get("longQuantity", 0)
        short_qty = pos.get("shortQuantity", 0)
        quantity = long_qty - short_qty

        market_value = pos.get("marketValue", 0)
        avg_cost = pos.get("averageCostBasis")
        cost_basis = avg_cost * abs(quantity) if avg_cost is not None else None

        position_data = {
            "symbol": instrument.get("symbol"),
            "description": instrument.get("description"),
            "asset_type": instrument.get("assetType"),
            "quantity": quantity,
            "market_value": market_value,
            "average_price": pos.get("averagePrice"),
            "cost_per_share": avg_cost,
            "cost_basis": cost_basis,
            "day_change": pos.get("currentDayProfitLoss"),
            "day_change_percent": pos.get("currentDayProfitLossPercentage"),
        }

        # Calculate gain/loss if we have cost basis
        if cost_basis is not None and market_value:
            position_data["gain_loss"] = market_value - cost_basis
            if cost_basis != 0:
                position_data["gain_loss_percent"] = (
                    (market_value - cost_basis) / cost_basis * 100
                )
            else:
                position_data["gain_loss_percent"] = 0

        positions.append(position_data)

    return {"account_id": account_hash, "positions": positions}


async def get_account(client: SchwabClient, args: dict) -> dict[str, Any]:
    """
    Get account information including type and balances.

    Args:
        client: SchwabClient instance
        args: Tool arguments (optional account_id)

    Returns:
        Dict with account info and balances
    """
    account_hash = await get_account_hash(client, args.get("account_id"))

    response = await client.get_account(account_hash)
    account_data = response.get("securitiesAccount", response)

    account_type = account_data.get("type", "UNKNOWN")

    # Taxable account types
    taxable_types = {"INDIVIDUAL", "JOINT", "TRUST", "CORPORATE"}

    # Get balances from appropriate field
    balances = account_data.get("currentBalances", {})
    if not balances:
        balances = account_data.get("initialBalances", {})

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
        },
    }
