# Schwab MCP Server

A read-only Model Context Protocol (MCP) server for Charles Schwab API. Access your Schwab account data and market information through AI assistants like Claude, ChatGPT, and more.

## Features

- **Portfolio Analysis** - View positions with cost basis, quantity, and market value
- **Real-time Quotes** - Get current prices for stocks and ETFs
- **Options Data** - Access options chains with Greeks
- **Price History** - Historical OHLCV data for technical analysis
- **Account Info** - View account balances and details

**Security Note:** This server is strictly READ-ONLY. No trading or account modification functionality is implemented.

## Prerequisites

- Python 3.10 or higher
- A Charles Schwab Developer account with:
  - App Key (Client ID)
  - App Secret (Client Secret)
  - A valid Refresh Token
  - Callback URL configured

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/schwab-mcp-server.git
cd schwab-mcp-server
```

2. Create and activate a virtual environment:
```bash
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
SCHWAB_CLIENT_ID=your_app_key_here
SCHWAB_CLIENT_SECRET=your_app_secret_here
SCHWAB_CALLBACK_URL=https://127.0.0.1:8182/callback
SCHWAB_TOKEN_PATH=~/.schwab-mcp/token.json
LOG_LEVEL=INFO
```

### Initial Token Setup

Create the token file at the path specified in `SCHWAB_TOKEN_PATH` (default: `~/.schwab-mcp/token.json`):

```json
{
  "access_token": "",
  "refresh_token": "YOUR_REFRESH_TOKEN_HERE",
  "expires_at": 0,
  "token_type": "Bearer"
}
```

Setting `expires_at` to `0` forces an automatic token refresh on first use.

---

## Client Setup

### Claude Desktop

**macOS:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** Edit `%APPDATA%\Claude\claude_desktop_config.json`

Add the following configuration:

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
        "SCHWAB_TOKEN_PATH": "/path/to/.schwab-mcp/token.json"
      }
    }
  }
}
```

Restart Claude Desktop after saving the configuration.

---

### ChatGPT Desktop

ChatGPT Desktop supports MCP servers through its settings. To configure:

1. Open ChatGPT Desktop
2. Go to **Settings** > **Features** > **MCP Servers**
3. Click **Add Server** and enter:
   - **Name:** `schwab`
   - **Command:** `python`
   - **Arguments:** `-m schwab_mcp.server`
   - **Working Directory:** `/path/to/schwab-mcp-server`
4. Add the environment variables:
   - `SCHWAB_CLIENT_ID`: your_client_id
   - `SCHWAB_CLIENT_SECRET`: your_client_secret
   - `SCHWAB_CALLBACK_URL`: https://127.0.0.1:8182/callback
   - `SCHWAB_TOKEN_PATH`: /path/to/.schwab-mcp/token.json
5. Save and restart ChatGPT Desktop

---

### Claude Code (CLI)

Add the MCP server to your Claude Code configuration. Create or edit `~/.claude/claude_code_config.json`:

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
        "SCHWAB_TOKEN_PATH": "/path/to/.schwab-mcp/token.json"
      }
    }
  }
}
```

Alternatively, you can add it to your project's `.claude/settings.json` for project-specific configuration:

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
        "SCHWAB_TOKEN_PATH": "/path/to/.schwab-mcp/token.json"
      }
    }
  }
}
```

---

### OpenAI Codex

For Codex CLI, configure the MCP server in your environment:

1. Set up environment variables in your shell profile (`.bashrc`, `.zshrc`, etc.):
```bash
export SCHWAB_CLIENT_ID="your_client_id"
export SCHWAB_CLIENT_SECRET="your_client_secret"
export SCHWAB_CALLBACK_URL="https://127.0.0.1:8182/callback"
export SCHWAB_TOKEN_PATH="$HOME/.schwab-mcp/token.json"
```

2. Configure Codex to use the MCP server by adding to your Codex configuration:
```json
{
  "mcpServers": {
    "schwab": {
      "command": "python",
      "args": ["-m", "schwab_mcp.server"],
      "cwd": "/path/to/schwab-mcp-server"
    }
  }
}
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `get_account` | Get account information including type and balances |
| `get_positions` | Get all positions with cost basis and market value |
| `get_quote` | Get real-time quote for a single symbol |
| `get_quotes` | Get real-time quotes for multiple symbols |
| `get_option_chain` | Get options chain with Greeks for a symbol |
| `get_price_history` | Get historical OHLCV price data |

## Usage Examples

Once configured, you can ask your AI assistant questions like:

- "What are my current positions and their cost basis?"
- "Get me a quote for AAPL"
- "Show me the options chain for MSFT expiring in January"
- "What's the price history for NVDA over the last 6 months?"
- "What are my account balances?"

## Testing

### Using MCP Inspector

Test the server locally using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector python -m schwab_mcp.server
```

### Manual Test

Verify authentication is working:

```bash
python -c "from schwab_mcp.auth import TokenManager; from schwab_mcp.config import settings; tm = TokenManager(settings.schwab_client_id, settings.schwab_client_secret, settings.schwab_token_path); tm.load_token(); print('Token loaded successfully')"
```

## Troubleshooting

### Token Refresh Fails
- Ensure your refresh token is valid and not expired (7-day expiration)
- Verify your client ID and secret are correct
- Check that your Schwab Developer app is approved and active

### Server Won't Start
- Verify Python 3.10+ is installed: `python --version`
- Ensure all dependencies are installed: `pip install -e .`
- Check that the `.env` file exists and has correct values

### No Data Returned
- Confirm your Schwab account has the appropriate permissions
- Check if markets are open (some data limited outside trading hours)
- Review logs for API error messages

## Security

- **Read-only access only** - No trading or account modification capabilities
- **Token storage** - Tokens are stored locally with restricted file permissions (600)
- **No credential logging** - Sensitive data is never written to logs
- **Environment variables** - Credentials should be passed via environment, not hardcoded

## References

- [Schwab Developer Portal](https://developer.schwab.com/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## License

MIT - Use at your own risk. Not affiliated with Charles Schwab.
