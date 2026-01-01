"""
Database utilities for portfolio management with SQLite
Handles portfolio data persistence and retrieval
"""
import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PortfolioDB:
    """Manages portfolio data in SQLite database"""
    
    def __init__(self, db_path: str = "data/portfolio.db"):
        """Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Portfolio holdings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    name TEXT,
                    quantity REAL NOT NULL,
                    purchase_price REAL,
                    purchase_date TEXT,
                    sector TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol)
                )
            """)
            
            # Portfolio metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_value REAL,
                    cash_balance REAL,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Analysis history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_type TEXT,
                    symbol TEXT,
                    result TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_portfolio_from_json(self, json_file_path: str) -> bool:
        """Load portfolio data from JSON file and save to database
        
        Args:
            json_file_path: Path to portfolio JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(json_file_path, 'r') as f:
                portfolio_data = json.load(f)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clear existing data
                cursor.execute("DELETE FROM portfolio")
                cursor.execute("DELETE FROM portfolio_metadata")
                
                # Insert holdings
                holdings = portfolio_data.get('holdings', [])
                for holding in holdings:
                    cursor.execute("""
                        INSERT OR REPLACE INTO portfolio 
                        (symbol, name, quantity, purchase_price, purchase_date, sector)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        holding.get('symbol'),
                        holding.get('name'),
                        holding.get('quantity'),
                        holding.get('purchase_price'),
                        holding.get('purchase_date'),
                        holding.get('sector')
                    ))
                
                # Insert metadata
                cursor.execute("""
                    INSERT INTO portfolio_metadata (total_value, cash_balance)
                    VALUES (?, ?)
                """, (
                    portfolio_data.get('total_value', 0),
                    portfolio_data.get('cash_balance', 0)
                ))
                
                conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving portfolio: {e}")
            return False
    
    def get_portfolio(self) -> Dict[str, Any]:
        """Retrieve complete portfolio data from database
        
        Returns:
            Dict containing portfolio holdings and metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get holdings
            cursor.execute("SELECT * FROM portfolio ORDER BY symbol")
            holdings_rows = cursor.fetchall()
            holdings = [dict(row) for row in holdings_rows]
            
            # Get metadata
            cursor.execute("""
                SELECT * FROM portfolio_metadata 
                ORDER BY last_updated DESC LIMIT 1
            """)
            metadata_row = cursor.fetchone()
            metadata = dict(metadata_row) if metadata_row else {}
            
            return {
                'holdings': holdings,
                'metadata': metadata,
                'total_holdings': len(holdings)
            }
    
    def get_holdings_by_sector(self, sector: str) -> List[Dict]:
        """Get holdings filtered by sector"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM portfolio WHERE sector = ? ORDER BY symbol",
                (sector,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_holding(self, symbol: str) -> Optional[Dict]:
        """Get specific holding by symbol"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM portfolio WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_holding(self, symbol: str, **kwargs) -> bool:
        """Update holding information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
                values = list(kwargs.values()) + [symbol]
                cursor.execute(
                    f"UPDATE portfolio SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE symbol = ?",
                    values
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"Error updating holding: {e}")
            return False
    
    def save_analysis(self, analysis_type: str, symbol: str, result: str):
        """Save analysis result to history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analysis_history (analysis_type, symbol, result)
                VALUES (?, ?, ?)
            """, (analysis_type, symbol, result))
            conn.commit()
    
    def get_recent_analyses(self, limit: int = 10) -> List[Dict]:
        """Get recent analysis history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analysis_history 
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    portfolio_db = PortfolioDB()
    portfolio_db.save_portfolio_from_json("data/portfolio.json")
    logger.info("portofolio db loaded successfully from json file")
