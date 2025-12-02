"""Tests for the tools module."""

from datetime import datetime

import pytest

from schwab_mcp.tools.history import _date_to_epoch_ms, _epoch_ms_to_iso, _parse_candle
from schwab_mcp.tools.options import _parse_option_contract, _parse_option_map
from schwab_mcp.tools.quotes import _parse_quote


class TestQuoteParsing:
    """Tests for quote parsing utilities."""

    def test_parse_quote_full_data(self):
        """Test parsing a complete quote response."""
        data = {
            "assetMainType": "EQUITY",
            "quote": {
                "lastPrice": 150.25,
                "bidPrice": 150.20,
                "askPrice": 150.30,
                "bidSize": 100,
                "askSize": 200,
                "totalVolume": 50000000,
                "highPrice": 152.00,
                "lowPrice": 149.00,
                "openPrice": 150.00,
                "closePrice": 149.50,
                "netChange": 0.75,
                "netPercentChange": 0.50,
                "52WeekHigh": 180.00,
                "52WeekLow": 120.00,
                "peRatio": 25.5,
                "divYield": 0.65,
            },
            "reference": {
                "marketCap": 2500000000000,
                "exchange": "NASDAQ",
                "description": "Apple Inc.",
            },
        }
        result = _parse_quote("AAPL", data)

        assert result["symbol"] == "AAPL"
        assert result["asset_type"] == "EQUITY"
        assert result["last_price"] == 150.25
        assert result["bid"] == 150.20
        assert result["ask"] == 150.30
        assert result["bid_size"] == 100
        assert result["ask_size"] == 200
        assert result["volume"] == 50000000
        assert result["day_high"] == 152.00
        assert result["day_low"] == 149.00
        assert result["day_open"] == 150.00
        assert result["prev_close"] == 149.50
        assert result["day_change"] == 0.75
        assert result["day_change_percent"] == 0.50
        assert result["52_week_high"] == 180.00
        assert result["52_week_low"] == 120.00
        assert result["pe_ratio"] == 25.5
        assert result["div_yield"] == 0.65
        assert result["market_cap"] == 2500000000000
        assert result["exchange"] == "NASDAQ"
        assert result["description"] == "Apple Inc."

    def test_parse_quote_minimal_data(self):
        """Test parsing a quote with minimal data."""
        data = {
            "assetMainType": "EQUITY",
            "quote": {
                "lastPrice": 100.00,
            },
            "reference": {},
        }
        result = _parse_quote("XYZ", data)

        assert result["symbol"] == "XYZ"
        assert result["asset_type"] == "EQUITY"
        assert result["last_price"] == 100.00
        assert result["bid"] is None
        assert result["ask"] is None

    def test_parse_quote_empty_data(self):
        """Test parsing a quote with empty data."""
        result = _parse_quote("UNKNOWN", {})

        assert result["symbol"] == "UNKNOWN"
        assert result["asset_type"] is None
        assert result["last_price"] is None


class TestOptionParsing:
    """Tests for option parsing utilities."""

    def test_parse_option_contract(self):
        """Test parsing a single option contract."""
        contract_data = [
            {
                "symbol": "AAPL240119C00150000",
                "description": "AAPL Jan 19 2024 150 Call",
                "expirationDate": "2024-01-19",
                "daysToExpiration": 30,
                "bid": 5.50,
                "ask": 5.60,
                "last": 5.55,
                "mark": 5.55,
                "totalVolume": 1000,
                "openInterest": 5000,
                "volatility": 0.25,
                "delta": 0.55,
                "gamma": 0.05,
                "theta": -0.10,
                "vega": 0.20,
                "rho": 0.05,
                "inTheMoney": True,
                "intrinsicValue": 2.00,
                "extrinsicValue": 3.55,
                "timeValue": 3.55,
            }
        ]
        result = _parse_option_contract("150.0", contract_data)

        assert result["symbol"] == "AAPL240119C00150000"
        assert result["strike"] == 150.0
        assert result["expiration"] == "2024-01-19"
        assert result["days_to_expiration"] == 30
        assert result["bid"] == 5.50
        assert result["ask"] == 5.60
        assert result["delta"] == 0.55
        assert result["gamma"] == 0.05
        assert result["theta"] == -0.10
        assert result["vega"] == 0.20
        assert result["in_the_money"] is True

    def test_parse_option_contract_empty_list(self):
        """Test parsing returns None for empty contract list."""
        result = _parse_option_contract("150.0", [])
        assert result is None

    def test_parse_option_map(self):
        """Test parsing option expiration date map."""
        exp_date_map = {
            "2024-01-19:30": {
                "150.0": [
                    {
                        "symbol": "AAPL240119C00150000",
                        "expirationDate": "2024-01-19",
                        "strike": 150.0,
                        "delta": 0.55,
                    }
                ],
                "155.0": [
                    {
                        "symbol": "AAPL240119C00155000",
                        "expirationDate": "2024-01-19",
                        "strike": 155.0,
                        "delta": 0.45,
                    }
                ],
            }
        }
        result = _parse_option_map(exp_date_map)

        assert len(result) == 2
        # Should be sorted by expiration, then strike
        assert result[0]["strike"] == 150.0
        assert result[1]["strike"] == 155.0


class TestHistoryParsing:
    """Tests for price history parsing utilities."""

    def test_date_to_epoch_ms(self):
        """Test converting date string to epoch milliseconds."""
        result = _date_to_epoch_ms("2024-01-15")
        # Verify it's a reasonable epoch timestamp for 2024
        assert result > 1700000000000  # After 2023
        assert result < 1800000000000  # Before 2027

    def test_epoch_ms_to_iso(self):
        """Test converting epoch milliseconds to ISO string."""
        # Use a known timestamp: 2024-01-15 00:00:00 UTC would be around this
        epoch_ms = 1705276800000  # Approximately 2024-01-15
        result = _epoch_ms_to_iso(epoch_ms)

        # Result should be an ISO format string
        assert "2024-01-1" in result or "2024-01-0" in result  # Around mid-January

    def test_parse_candle(self):
        """Test parsing a single candle."""
        candle = {
            "datetime": 1705276800000,  # Epoch ms
            "open": 150.00,
            "high": 152.00,
            "low": 149.00,
            "close": 151.50,
            "volume": 1000000,
        }
        result = _parse_candle(candle)

        assert "datetime" in result
        assert result["open"] == 150.00
        assert result["high"] == 152.00
        assert result["low"] == 149.00
        assert result["close"] == 151.50
        assert result["volume"] == 1000000

    def test_parse_candle_missing_fields(self):
        """Test parsing a candle with missing optional fields."""
        candle = {
            "datetime": 1705276800000,
            "close": 100.00,
        }
        result = _parse_candle(candle)

        assert result["close"] == 100.00
        assert result["open"] is None
        assert result["high"] is None
        assert result["low"] is None
        assert result["volume"] is None
