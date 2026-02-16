import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

# Constants
START_DATE = "2010-01-01"
BENCHMARK_SYMBOL = "NIFTY_50"

def generate_random_walk(start_price, days, drift=0.0003, volatility=0.015):
    """Generates a geometric Brownian motion price series."""
    returns = np.random.normal(loc=drift, scale=volatility, size=days)
    price_paths = start_price * np.exp(np.cumsum(returns))
    return price_paths

def generate_historical_data(portfolio_path="data/portfolio.json"):
    """
    Generates a DataFrame of historical closing prices for all assets in portfolio
    plus a benchmark, starting from 2010.
    """
    # 1. Load Symbols from Portfolio
    try:
        # Construct absolute path if needed, or use relative
        if not os.path.exists(portfolio_path):
            # Try looking one level up if run from pages/
            if os.path.exists(os.path.join("..", portfolio_path)):
                portfolio_path = os.path.join("..", portfolio_path)
        
        with open(portfolio_path, 'r') as f:
            data = json.load(f)
            # key 'symbol' in holdings
            symbols = [h['symbol'] for h in data.get('holdings', [])]
            # Add watchlist items if you want
            symbols.extend(data.get('watch_list', []))
            # Remove duplicates
            symbols = list(set(symbols))
            
    except Exception as e:
        print(f"Warning: Could not load portfolio for symbols ({e}). Using defaults.")
        symbols = ["RELIANCE.BSE", "TCS.BSE", "HDFCBANK.BSE", "INFY.BSE", "ITC.BSE"]

    if not symbols:
         symbols = ["RELIANCE.BSE", "TCS.BSE", "HDFCBANK.BSE", "INFY.BSE", "ITC.BSE"]

    # 2. Setup Date Range
    end_date = datetime.now()
    start_date = datetime.strptime(START_DATE, "%Y-%m-%d")
    date_range = pd.date_range(start=start_date, end=end_date, freq='B') # Business days
    days = len(date_range)

    # 3. Generate Data
    df = pd.DataFrame(index=date_range)
    
    # Generate Benchmark (NIFTY 50 approx behavior)
    np.random.seed(42) # Fixed seed for consistency
    df[BENCHMARK_SYMBOL] = generate_random_walk(start_price=5000, days=days, drift=0.0004, volatility=0.01)

    # Generate Individual Stocks
    for symbol in symbols:
        # Randomize parameters for variety
        vol = np.random.uniform(0.01, 0.025)
        drift = np.random.uniform(0.0001, 0.0005)
        initial_price = np.random.uniform(100, 2000)
        
        df[symbol] = generate_random_walk(start_price=initial_price, days=days, drift=drift, volatility=vol)

    df.index.name = "Date"
    return df

if __name__ == "__main__":
    df = generate_historical_data()
    df.to_parquet("data/historical_data.parquet")
    print(f"Generated data for {len(df.columns)} assets over {len(df)} days.")
    print(df.tail())