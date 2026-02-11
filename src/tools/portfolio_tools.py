"""
Tools for portfolio agents to interact with portfolio data
"""
from langchain.tools import tool
from typing import Dict, List, Optional
from src.utils.db_utils import PortfolioDB
import json

# Initialize database instance
portfolio_db = PortfolioDB()


@tool
def get_portfolio_data() -> str:
    """
    Retrieve complete portfolio holdings and metadata.
    Returns portfolio data including all holdings, sectors, and total value.
    
    Returns:
        str: JSON string of portfolio data
    """
    portfolio = portfolio_db.get_portfolio()
    return json.dumps(portfolio, indent=2)


@tool
def get_holding_info(symbol: str) -> str:
    """
    Get detailed information about a specific holding.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'GOOGL')
    
    Returns:
        str: JSON string of holding details or error message
    """
    import json
    holding = portfolio_db.get_holding(symbol.upper())
    if holding:
        return json.dumps(holding, indent=2)
    return f"No holding found for symbol: {symbol}"


@tool
def get_holdings_by_sector(sector: str) -> str:
    """
    Get all holdings in a specific sector.
    
    Args:
        sector: Sector name (e.g., 'Technology', 'Healthcare')
    
    Returns:
        str: JSON string of holdings in the sector
    """
    import json
    holdings = portfolio_db.get_holdings_by_sector(sector)
    return json.dumps(holdings, indent=2)


@tool
def calculate_portfolio_value(current_prices: str) -> str:
    """
    Calculate current portfolio value given current prices.
    
    Args:
        current_prices: JSON string with symbol:price mapping
    
    Returns:
        str: Portfolio valuation summary
    """
    import json
    try:
        prices = json.loads(current_prices)
        portfolio = portfolio_db.get_portfolio()
        
        total_value = 0
        holdings_value = []
        
        for holding in portfolio['holdings']:
            symbol = holding['symbol']
            quantity = holding['quantity']
            current_price = prices.get(symbol, 0)
            value = quantity * current_price
            total_value += value
            
            holdings_value.append({
                'symbol': symbol,
                'quantity': quantity,
                'current_price': current_price,
                'value': value
            })
        
        result = {
            'total_value': total_value,
            'holdings_value': holdings_value
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error calculating portfolio value: {str(e)}"


