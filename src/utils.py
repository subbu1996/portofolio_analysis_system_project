"""Utility functions for the portfolio agent system."""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def pretty_print_messages(update: dict, stream_mode: str = "updates"):
    """Pretty print agent messages for debugging.
    
    Args:
        update: Update from graph stream
        stream_mode: Streaming mode ('updates' or 'values')
    """
    
    for node_name, node_update in update.items():
        print(f"\n{'='*60}")
        print(f"Update from node: {node_name}")
        print(f"{'='*60}")
        
        if "messages" in node_update:
            messages = node_update["messages"]
            if isinstance(messages, list):
                
                for msg in messages[-1:]:  # Show only last message
                    if hasattr(msg, 'content'):
                        print(f"\n{msg.content}\n")
                    elif hasattr(msg, 'pretty_repr'):
                        print(f"\n{msg.pretty_repr()}\n")
                    elif hasattr(msg, 'text'):
                        print(f"\n{msg.text}\n")
                        
def load_portfolio_from_file(filepath: str = None) -> dict:
    """Load portfolio data from JSON file.
    
    Args:
        filepath: Path to portfolio JSON file
        
    Returns:
        Portfolio data dictionary
    """
    if filepath is None:
        current_dir = os.getcwd()
        filepath = os.path.join(current_dir, "data", "portfolio.json")

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        logger.info(f"Portfolio data loaded from {filepath}")
        return data
    except FileNotFoundError:
        logger.error(f"Portfolio file not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in portfolio file: {e}")
        raise


def save_portfolio_to_file(portfolio_data: Dict[str, Any], file_path: str) -> None:
    """Save portfolio data to JSON file.
    
    Args:
        portfolio_data: Portfolio data dictionary
        file_path: Path to save JSON file
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(portfolio_data, f, indent=2, ensure_ascii=False)


def validate_portfolio_schema(portfolio_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate portfolio data against expected schema.
    
    Args:
        portfolio_data: Portfolio data to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["holdings", "transactions", "start_date"]
    
    for field in required_fields:
        if field not in portfolio_data:
            return False, f"Missing required field: {field}"
    
    # Validate holdings
    if not isinstance(portfolio_data["holdings"], list):
        return False, "holdings must be a list"
    
    for i, holding in enumerate(portfolio_data["holdings"]):
        required_holding_fields = ["symbol", "asset_type", "quantity", "avg_price"]
        for field in required_holding_fields:
            if field not in holding:
                return False, f"Holding {i} missing required field: {field}"
    
    # Validate transactions
    if not isinstance(portfolio_data["transactions"], list):
        return False, "transactions must be a list"
    
    for i, transaction in enumerate(portfolio_data["transactions"]):
        required_transaction_fields = ["date", "symbol", "transaction_type", "quantity", "price"]
        for field in required_transaction_fields:
            if field not in transaction:
                return False, f"Transaction {i} missing required field: {field}"
    
    return True, None


def format_currency(amount: float, currency: str = "INR") -> str:
    """Format amount as currency string.
    
    Args:
        amount: Amount to format
        currency: Currency code (default: INR)
    
    Returns:
        Formatted currency string
    """
    if currency == "INR":
        # Indian numbering system (lakhs, crores)
        if amount >= 10000000:  # 1 crore
            return f"₹{amount/10000000:.2f} Cr"
        elif amount >= 100000:  # 1 lakh
            return f"₹{amount/100000:.2f} L"
        else:
            return f"₹{amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"


def get_indian_stock_exchanges() -> Dict[str, str]:
    """Get list of supported Indian stock exchanges.
    
    Returns:
        Dict mapping exchange codes to names
    """
    return {
        "NSE": "National Stock Exchange of India",
        "BSE": "Bombay Stock Exchange",
    }


def parse_stock_symbol(symbol: str) -> tuple[str, str]:
    """Parse stock symbol to extract ticker and exchange.
    
    Args:
        symbol: Stock symbol (e.g., "RELIANCE.NSE")
    
    Returns:
        Tuple of (ticker, exchange)
    
    Raises:
        ValueError: If symbol format is invalid
    """
    if "." not in symbol:
        raise ValueError(f"Invalid symbol format: {symbol}. Expected format: TICKER.EXCHANGE")
    
    parts = symbol.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid symbol format: {symbol}")
    
    ticker, exchange = parts
    
    if exchange not in ["NSE", "BSE"]:
        raise ValueError(f"Unsupported exchange: {exchange}. Supported: NSE, BSE")
    
    return ticker, exchange
