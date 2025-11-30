"""
Schwab MCP Server - Main entry point

Exposes Schwab API data to Claude via Model Context Protocol.
READ-ONLY: No trading functionality.
"""

import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .auth import TokenManager
from .client import SchwabClient
from .config import settings
from .tools import account, history, options, quotes

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings().log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Global instances (initialized lazily)
_token_manager: TokenManager | None = None
_schwab_client: SchwabClient | None = None


def get_token_manager() -> TokenManager:
    """Get or create TokenManager instance."""
    global _token_manager
    if _token_manager is None:
        cfg = settings()
        _token_manager = TokenManager(
            client_id=cfg.schwab_client_id,
            client_secret=cfg.schwab_client_secret,
            token_path=cfg.schwab_token_path,
        )
    return _token_manager


def get_schwab_client() -> SchwabClient:
    """Get or create SchwabClient instance."""
    global _schwab_client
    if _schwab_client is None:
        cfg = settings()
        _schwab_client = SchwabClient(
            token_manager=get_token_manager(),
            timeout=cfg.schwab_timeout,
        )
    return _schwab_client


# Initialize MCP server
server = Server("schwab-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="get_positions",
            description="Get all positions with cost basis, quantity, market value, and gain/loss for an account",
            inputSchema=account.GET_POSITIONS_SCHEMA,
        ),
        Tool(
            name="get_account",
            description="Get account information including type (IRA, taxable, etc.) and balances",
            inputSchema=account.GET_ACCOUNT_SCHEMA,
        ),
        Tool(
            name="get_quote",
            description="Get real-time quote for a stock symbol including price, bid/ask, volume, and fundamentals",
            inputSchema=quotes.GET_QUOTE_SCHEMA,
        ),
        Tool(
            name="get_quotes",
            description="Get real-time quotes for multiple symbols at once",
            inputSchema=quotes.GET_QUOTES_SCHEMA,
        ),
        Tool(
            name="get_option_chain",
            description="Get options chain with Greeks (delta, gamma, theta, vega) for a symbol",
            inputSchema=options.GET_OPTION_CHAIN_SCHEMA,
        ),
        Tool(
            name="get_price_history",
            description="Get historical OHLCV price data for technical analysis",
            inputSchema=history.GET_PRICE_HISTORY_SCHEMA,
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool invocations."""
    logger.info(f"Tool called: {name}")
    logger.debug(f"Arguments: {arguments}")

    client = get_schwab_client()

    handlers: dict[str, Any] = {
        "get_positions": lambda args: account.get_positions(client, args),
        "get_account": lambda args: account.get_account(client, args),
        "get_quote": lambda args: quotes.get_quote(client, args),
        "get_quotes": lambda args: quotes.get_quotes(client, args),
        "get_option_chain": lambda args: options.get_option_chain(client, args),
        "get_price_history": lambda args: history.get_price_history(client, args),
    }

    handler = handlers.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")

    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}", exc_info=True)
        error_response = {
            "error": True,
            "error_type": type(e).__name__,
            "message": str(e),
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def run_server():
    """Run the MCP server."""
    logger.info("Starting Schwab MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Entry point for the server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
