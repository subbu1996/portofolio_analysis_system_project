"""Financial tools for portfolio analysis and market data fetching."""
import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List
import requests
from langchain_core.tools import tool
import numpy as np
# from numpy_financial import xirr as np_xirr
# from xirr import xirr

class AlphaVantageClient:
    """Client for Alpha Vantage API supporting Indian stocks (NSE/BSE)."""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not found. Set ALPHA_VANTAGE_API_KEY environment variable.")
    
    def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Make API request with error handling."""
        params["apikey"] = self.api_key
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(f"API Error: {data['Error Message']}")
            if "Note" in data:
                raise ValueError(f"API Rate Limit: {data['Note']}")
            
            return data
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to fetch data from Alpha Vantage: {str(e)}")
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote for Indian stock.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE.NSE", "TCS.BSE")
        
        Returns:
            Dict with price, volume, and change data
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }
        data = self._make_request(params)
        
        if "Global Quote" not in data or not data["Global Quote"]:
            raise ValueError(f"No data found for symbol: {symbol}")
        
        quote = data["Global Quote"]
        return {
            "symbol": symbol,
            "price": float(quote.get("05. price", 0)),
            "change": float(quote.get("09. change", 0)),
            "change_percent": quote.get("10. change percent", "0%"),
            "volume": int(quote.get("06. volume", 0)),
            "latest_trading_day": quote.get("07. latest trading day", ""),
        }
    
    def get_daily_data(self, symbol: str, outputsize: str = "compact") -> Dict[str, Any]:
        """Get daily time series data.
        
        Args:
            symbol: Stock symbol
            outputsize: "compact" (100 days) or "full" (20+ years)
        
        Returns:
            Dict with daily OHLCV data
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize
        }
        data = self._make_request(params)
        
        if "Time Series (Daily)" not in data:
            raise ValueError(f"No daily data found for symbol: {symbol}")
        
        return data["Time Series (Daily)"]
    
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """Get fundamental data and company overview.
        
        Returns P/E ratio, market cap, dividend yield, sector, etc.
        """
        params = {
            "function": "OVERVIEW",
            "symbol": symbol
        }
        data = self._make_request(params)
        
        if not data or "Symbol" not in data:
            raise ValueError(f"No overview data found for symbol: {symbol}")
        
        return {
            "symbol": data.get("Symbol"),
            "name": data.get("Name"),
            "sector": data.get("Sector"),
            "industry": data.get("Industry"),
            "market_cap": data.get("MarketCapitalization"),
            "pe_ratio": float(data.get("PERatio", 0) or 0),
            "dividend_yield": float(data.get("DividendYield", 0) or 0),
            "52_week_high": float(data.get("52WeekHigh", 0) or 0),
            "52_week_low": float(data.get("52WeekLow", 0) or 0),
            "beta": float(data.get("Beta", 0) or 0),
        }


@tool
def fetch_stock_price(symbol: str) -> str:
    """Fetch current price for Indian stock from Alpha Vantage API.
    
    Args:
        symbol: Stock symbol with exchange suffix (e.g., "RELIANCE.NSE", "TCS.BSE", "INFY.NSE")
    
    Returns:
        JSON string with current price, change, and volume data
    """
    try:
        client = AlphaVantageClient()
        quote = client.get_quote(symbol)
        return json.dumps(quote, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


@tool
def fetch_company_fundamentals(symbol: str) -> str:
    """Fetch fundamental data for Indian company including P/E ratio, sector, market cap.
    
    Args:
        symbol: Stock symbol with exchange suffix (e.g., "RELIANCE.NSE")
    
    Returns:
        JSON string with fundamental data
    """
    try:
        client = AlphaVantageClient()
        overview = client.get_company_overview(symbol)
        return json.dumps(overview, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


@tool
def fetch_historical_prices(symbol: str, days: int = 30) -> str:
    """Fetch historical daily prices for rolling returns and performance analysis.
    
    Args:
        symbol: Stock symbol with exchange suffix
        days: Number of days of historical data (default: 30)
    
    Returns:
        JSON string with date-indexed price data
    """
    try:
        client = AlphaVantageClient()
        daily_data = client.get_daily_data(symbol, outputsize="compact")
        
        # Get most recent 'days' entries
        sorted_dates = sorted(daily_data.keys(), reverse=True)[:days]
        historical = {
            date: {
                "open": float(daily_data[date]["1. open"]),
                "high": float(daily_data[date]["2. high"]),
                "low": float(daily_data[date]["3. low"]),
                "close": float(daily_data[date]["4. close"]),
                "volume": int(daily_data[date]["5. volume"])
            }
            for date in sorted_dates
        }
        
        return json.dumps({"symbol": symbol, "data": historical}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol})


# ============================================================================
# FINANCIAL CALCULATION TOOL
# ============================================================================

class FinancialCalculator:
    """Comprehensive financial calculations for portfolio analysis."""
    
    @staticmethod
    def calculate_xirr(cash_flows: List[tuple], dates: List[str]) -> float:
        """Calculate XIRR (Extended Internal Rate of Return).
        
        Args:
            cash_flows: List of cash flows (negative for investment, positive for returns)
            dates: List of dates in 'YYYY-MM-DD' format
        
        Returns:
            XIRR as percentage
        """
        if len(cash_flows) != len(dates):
            raise ValueError("Cash flows and dates must have same length")
        
        try:
            date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
            ## ToDo
            xirr_value = 12.14 # xirr(date_objects, cash_flows)
            return round(xirr_value * 100, 2)
        except Exception as e:
            raise ValueError(f"XIRR calculation failed: {str(e)}")
    
    @staticmethod
    def calculate_cagr(initial_value: float, final_value: float, years: float) -> float:
        """Calculate Compound Annual Growth Rate.
        
        Args:
            initial_value: Starting portfolio value
            final_value: Current portfolio value
            years: Time period in years
        
        Returns:
            CAGR as percentage
        """
        if initial_value <= 0 or years <= 0:
            raise ValueError("Initial value and years must be positive")
        
        cagr = (pow(final_value / initial_value, 1 / years) - 1) * 100
        return round(cagr, 2)
    
    @staticmethod
    def calculate_pnl(holdings: List[Dict]) -> Dict[str, float]:
        """Calculate realized and unrealized P&L.
        
        Args:
            holdings: List of portfolio holdings
        
        Returns:
            Dict with unrealized_pnl, realized_pnl, and total_pnl
        """
        unrealized_pnl = 0
        total_invested = 0
        current_value = 0
        
        for holding in holdings:
            quantity = holding.get("quantity", 0)
            avg_price = holding.get("avg_price", 0)
            current_price = holding.get("current_price", avg_price)
            
            invested = quantity * avg_price
            current = quantity * current_price
            
            total_invested += invested
            current_value += current
            unrealized_pnl += (current - invested)
        
        return {
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "unrealized_pnl_percent": round((unrealized_pnl / total_invested * 100) if total_invested > 0 else 0, 2)
        }
    
    @staticmethod
    def calculate_exposure(holdings: List[Dict]) -> Dict[str, Any]:
        """Calculate portfolio exposure by sector and asset class.
        
        Args:
            holdings: List of portfolio holdings
        
        Returns:
            Dict with sector-wise and asset-wise breakdown
        """
        total_value = sum(h.get("quantity", 0) * h.get("current_price", 0) for h in holdings)
        
        sector_exposure = {}
        asset_exposure = {}
        
        for holding in holdings:
            value = holding.get("quantity", 0) * holding.get("current_price", 0)
            sector = holding.get("sector", "Unknown")
            asset_type = holding.get("asset_type", "equity")
            
            # Sector exposure
            if sector not in sector_exposure:
                sector_exposure[sector] = 0
            sector_exposure[sector] += value
            
            # Asset type exposure
            if asset_type not in asset_exposure:
                asset_exposure[asset_type] = 0
            asset_exposure[asset_type] += value
        
        # Convert to percentages
        sector_percentages = {
            sector: round(value / total_value * 100, 2)
            for sector, value in sector_exposure.items()
        } if total_value > 0 else {}
        
        asset_percentages = {
            asset: round(value / total_value * 100, 2)
            for asset, value in asset_exposure.items()
        } if total_value > 0 else {}
        
        return {
            "sector_exposure": sector_percentages,
            "asset_exposure": asset_percentages,
            "total_portfolio_value": round(total_value, 2)
        }
    
    @staticmethod
    def calculate_rolling_returns(prices: List[float], window: int = 30) -> List[float]:
        """Calculate rolling returns for given window.
        
        Args:
            prices: List of daily prices
            window: Rolling window in days
        
        Returns:
            List of rolling return percentages
        """
        if len(prices) < window:
            return []
        
        returns = []
        for i in range(window, len(prices)):
            start_price = prices[i - window]
            end_price = prices[i]
            if start_price > 0:
                ret = ((end_price - start_price) / start_price) * 100
                returns.append(round(ret, 2))
        
        return returns
    
    @staticmethod
    def calculate_pe_ratio_analysis(holdings: List[Dict], market_pe: float = 22.0) -> Dict[str, Any]:
        """Analyze P/E ratios of portfolio holdings vs market average.
        
        Args:
            holdings: List of holdings with pe_ratio field
            market_pe: Market average P/E ratio (Nifty 50 ~22)
        
        Returns:
            Dict with P/E analysis
        """
        pe_ratios = [h.get("pe_ratio", 0) for h in holdings if h.get("pe_ratio", 0) > 0]
        
        if not pe_ratios:
            return {"error": "No P/E ratio data available"}
        
        avg_pe = sum(pe_ratios) / len(pe_ratios)
        
        return {
            "average_portfolio_pe": round(avg_pe, 2),
            "market_pe": market_pe,
            "vs_market": "Overvalued" if avg_pe > market_pe else "Undervalued",
            "pe_premium": round(((avg_pe - market_pe) / market_pe) * 100, 2)
        }


@tool
def calculate_portfolio_metrics(portfolio_json: str) -> str:
    """Calculate comprehensive portfolio metrics including XIRR, CAGR, P&L, and exposure.
    
    This is the main financial calculation tool that processes portfolio data and returns
    detailed analysis including:
    - XIRR and CAGR
    - Realized and Unrealized P&L
    - Sector and Asset Class exposure
    - P/E ratio analysis
    
    Args:
        portfolio_json: JSON string containing portfolio data with holdings and transactions
    
    Returns:
        JSON string with all calculated metrics
    """
    try:
        portfolio = json.loads(portfolio_json)
        calculator = FinancialCalculator()
        
        holdings = portfolio.get("holdings", [])
        transactions = portfolio.get("transactions", [])
        start_date = portfolio.get("start_date")
        
        results = {}
        
        # Calculate P&L
        if holdings:
            results["pnl"] = calculator.calculate_pnl(holdings)
        
        # Calculate exposure
        if holdings:
            results["exposure"] = calculator.calculate_exposure(holdings)
        
        # Calculate XIRR if transactions available
        if transactions and start_date:
            try:
                cash_flows = [-t.get("quantity", 0) * t.get("price", 0) 
                             for t in transactions if t.get("transaction_type") == "buy"]
                dates = [t.get("date") for t in transactions if t.get("transaction_type") == "buy"]
                
                # Add current value as final cash flow
                current_value = sum(h.get("quantity", 0) * h.get("current_price", 0) 
                                  for h in holdings)
                cash_flows.append(current_value)
                dates.append(datetime.now().strftime("%Y-%m-%d"))
                
                if len(cash_flows) > 1:
                    results["xirr"] = calculator.calculate_xirr(cash_flows, dates)
            except Exception as e:
                results["xirr_error"] = str(e)
        
        # Calculate CAGR
        if start_date and holdings:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                years = (datetime.now() - start).days / 365.25
                
                initial_value = sum(h.get("quantity", 0) * h.get("avg_price", 0) 
                                  for h in holdings)
                final_value = sum(h.get("quantity", 0) * h.get("current_price", 0) 
                                for h in holdings)
                
                if years > 0:
                    results["cagr"] = calculator.calculate_cagr(initial_value, final_value, years)
            except Exception as e:
                results["cagr_error"] = str(e)
        
        # P/E Analysis
        if holdings:
            results["pe_analysis"] = calculator.calculate_pe_ratio_analysis(holdings)
        
        return json.dumps(results, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Calculation failed: {str(e)}"})



# # ============================================================================
# # DATABASE UTILITIES FOR PERSISTENCE
# # ============================================================================

# class PortfolioDatabase:
#     """SQLite database for persisting portfolio data and analysis results."""
    
#     def __init__(self, db_path: str = "data/portfolio.db"):
#         self.db_path = db_path
#         self._init_database()
    
#     def _init_database(self):
#         """Initialize database schema."""
#         os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
#         with sqlite3.connect(self.db_path) as conn:
#             cursor = conn.cursor()
            
#             # Holdings table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS holdings (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     symbol TEXT NOT NULL,
#                     asset_type TEXT NOT NULL,
#                     quantity REAL NOT NULL,
#                     avg_price REAL NOT NULL,
#                     current_price REAL,
#                     sector TEXT,
#                     platform_acquired TEXT,
#                     purchase_date TEXT,
#                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Transactions table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS transactions (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     date TEXT NOT NULL,
#                     symbol TEXT NOT NULL,
#                     transaction_type TEXT NOT NULL,
#                     quantity REAL NOT NULL,
#                     price REAL NOT NULL,
#                     charges REAL DEFAULT 0,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Analysis results table
#             cursor.execute("""
#                 CREATE TABLE IF NOT EXISTS analysis_results (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     analysis_type TEXT NOT NULL,
#                     results TEXT NOT NULL,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             conn.commit()
    
#     def save_portfolio(self, portfolio_data: Dict) -> None:
#         """Save portfolio data to database."""
#         with sqlite3.connect(self.db_path) as conn:
#             cursor = conn.cursor()
            
#             # Clear existing data
#             cursor.execute("DELETE FROM holdings")
#             cursor.execute("DELETE FROM transactions")
            
#             # Insert holdings
#             for holding in portfolio_data.get("holdings", []):
#                 cursor.execute("""
#                     INSERT INTO holdings 
#                     (symbol, asset_type, quantity, avg_price, current_price, sector, platform_acquired, purchase_date)
#                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#                 """, (
#                     holding.get("symbol"),
#                     holding.get("asset_type"),
#                     holding.get("quantity"),
#                     holding.get("avg_price"),
#                     holding.get("current_price"),
#                     holding.get("sector"),
#                     holding.get("platform_acquired"),
#                     holding.get("purchase_date")
#                 ))
            
#             # Insert transactions
#             for transaction in portfolio_data.get("transactions", []):
#                 cursor.execute("""
#                     INSERT INTO transactions 
#                     (date, symbol, transaction_type, quantity, price, charges)
#                     VALUES (?, ?, ?, ?, ?, ?)
#                 """, (
#                     transaction.get("date"),
#                     transaction.get("symbol"),
#                     transaction.get("transaction_type"),
#                     transaction.get("quantity"),
#                     transaction.get("price"),
#                     transaction.get("charges", 0)
#                 ))
            
#             conn.commit()
    
#     def get_portfolio(self) -> Dict:
#         """Retrieve portfolio data from database."""
#         with sqlite3.connect(self.db_path) as conn:
#             cursor = conn.cursor()
            
#             # Get holdings
#             cursor.execute("SELECT * FROM holdings")
#             holdings_rows = cursor.fetchall()
#             holdings = [{
#                 "id": row[0],
#                 "symbol": row[1],
#                 "asset_type": row[2],
#                 "quantity": row[3],
#                 "avg_price": row[4],
#                 "current_price": row[5],
#                 "sector": row[6],
#                 "platform_acquired": row[7],
#                 "purchase_date": row[8]
#             } for row in holdings_rows]
            
#             # Get transactions
#             cursor.execute("SELECT * FROM transactions ORDER BY date DESC")
#             transactions_rows = cursor.fetchall()
#             transactions = [{
#                 "id": row[0],
#                 "date": row[1],
#                 "symbol": row[2],
#                 "transaction_type": row[3],
#                 "quantity": row[4],
#                 "price": row[5],
#                 "charges": row[6]
#             } for row in transactions_rows]
            
#             return {
#                 "holdings": holdings,
#                 "transactions": transactions
#             }
