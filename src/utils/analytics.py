import pandas as pd
import numpy as np
from scipy import optimize
from datetime import datetime
import json

# --- Helper Functions ---
def xnpv(rate, values, dates):
    """Calculate Net Present Value for irregular intervals."""
    if rate <= -1.0:
        return float('inf')
    min_date = min(dates)
    return sum([val / ((1 + rate) ** ((date - min_date).days / 365.0)) for val, date in zip(values, dates)])

def calculate_xirr(transactions, current_value):
    """Calculate XIRR given a list of transaction dicts and current portfolio value."""
    if not transactions:
        return 0.0
        
    dates = [pd.to_datetime(t['date']) for t in transactions]
    amounts = [t['amount'] for t in transactions] # Negative for buy, Positive for sell
    
    # Append current value as if we sold everything today
    dates.append(datetime.now())
    amounts.append(current_value)
    
    try:
        return optimize.newton(lambda r: xnpv(r, amounts, dates), 0.1)
    except (RuntimeError, OverflowError):
        return 0.0

def calculate_max_drawdown(series):
    """Calculates Maximum Drawdown series and scalar."""
    if series.empty:
        return pd.Series(), 0.0
    
    rolling_max = series.cummax()
    drawdown = (series - rolling_max) / rolling_max
    max_dd = drawdown.min()
    return drawdown * 100, max_dd * 100

def calculate_risk_metrics(daily_returns, benchmark_returns):
    """Calculates Beta and Sharpe Ratio."""
    if daily_returns.empty or len(daily_returns) < 2:
        return 0.0, 0.0
    
    # Align dates
    df = pd.concat([daily_returns, benchmark_returns], axis=1, join='inner').dropna()
    if df.empty:
        return 0.0, 0.0
        
    # Beta
    cov_matrix = np.cov(df.iloc[:, 0], df.iloc[:, 1])
    beta = cov_matrix[0, 1] / cov_matrix[1, 1]
    
    # Sharpe (Assuming risk-free rate ~6%)
    rf_daily = (1 + 0.06) ** (1/252) - 1
    excess_returns = df.iloc[:, 0] - rf_daily
    sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() != 0 else 0
    
    return beta, sharpe

# --- Main Processing Logic ---
def process_portfolio_data(portfolio_data, historical_prices_df, selected_symbols=None):
    """
    Core engine to process portfolio data with filtering and benchmark comparison.
    
    Args:
        portfolio_data (dict): The JSON portfolio data.
        historical_prices_df (pd.DataFrame): Historical OHLC data.
        selected_symbols (list, optional): List of symbols to filter by. None = All.
    """
    
    # 1. Filter Transactions & Holdings
    tx_df = pd.DataFrame(portfolio_data['transactions'])
    tx_df['date'] = pd.to_datetime(tx_df['date'])
    
    if selected_symbols and 'ALL' not in selected_symbols:
        tx_df = tx_df[tx_df['symbol'].isin(selected_symbols)]
        
    if tx_df.empty:
        return None 

    # 2. Initialize Time Series
    # We clip the historical data to start from the first transaction of the *filtered* view
    start_date = tx_df['date'].min()
    hist_data = historical_prices_df[historical_prices_df.index >= start_date].copy()
    
    # Tracking Series
    dates = hist_data.index
    portfolio_units = pd.DataFrame(0.0, index=dates, columns=historical_prices_df.columns)
    benchmark_units = pd.Series(0.0, index=dates) # "Phantom" Nifty units
    
    invested_capital = pd.Series(0.0, index=dates)
    cash_flows = []

    cumulative_invested = 0.0
    
    # Benchmark Simulation Vars
    # We assume every time we invested ₹X in stock, we invested ₹X in Nifty
    nifty_col = "NIFTY_50"
    
    for date in dates:
        # Process transactions for this day
        days_tx = tx_df[tx_df['date'] == date]
        
        for _, row in days_tx.iterrows():
            sym = row['symbol']
            qty = row['quantity']
            price = row['price']
            tx_type = row['transaction_type']
            amount = (qty * price) + row.get('charges', 0)
            
            if tx_type == 'buy':
                # Portfolio Update
                if sym in portfolio_units.columns:
                    portfolio_units.loc[date:, sym] += qty
                
                # Benchmark Update (Buy equivalent Nifty units)
                nifty_price = hist_data.at[date, nifty_col]
                nifty_units_bought = amount / nifty_price
                benchmark_units.loc[date:] += nifty_units_bought
                
                cumulative_invested += amount
                cash_flows.append({'date': date, 'amount': -amount})
                
            elif tx_type == 'sell':
                if sym in portfolio_units.columns:
                    portfolio_units.loc[date:, sym] -= qty
                
                # Benchmark Update (Sell equivalent portion - simplified logic)
                # In real app, you'd track specific tax lots, here we just reduce proportional value
                # For simplicity in this demo, we accumulate 'invested' only on buys 
                # or reduce it proportionally. Keeping it simple: Invested = Cost Basis.
                cumulative_invested -= amount # Approximate
                cash_flows.append({'date': date, 'amount': amount})

        invested_capital.loc[date] = cumulative_invested

    # 3. Calculate Daily Values
    # Portfolio Value = Sum(Units * Price)
    # We strictly use columns that exist in both units and history (excluding Nifty for portfolio sum)
    valid_cols = [c for c in portfolio_units.columns if c != nifty_col]
    
    daily_portfolio_value = (portfolio_units[valid_cols] * hist_data[valid_cols]).sum(axis=1)
    daily_benchmark_value = benchmark_units * hist_data[nifty_col]
    
    # 4. Metrics & Returns
    current_pf_val = daily_portfolio_value.iloc[-1]
    current_bm_val = daily_benchmark_value.iloc[-1]
    current_invested = invested_capital.iloc[-1]
    
    # Percentage Profit Series ( (Value - Cost) / Cost * 100 )
    # Handle division by zero
    pf_profit_pct = ((daily_portfolio_value - invested_capital) / invested_capital * 100).fillna(0)
    bm_profit_pct = ((daily_benchmark_value - invested_capital) / invested_capital * 100).fillna(0)
    
    # Drawdown
    pf_drawdown, pf_max_dd = calculate_max_drawdown(daily_portfolio_value)
    
    # Risk Metrics
    pf_returns = daily_portfolio_value.pct_change().fillna(0)
    bm_returns = hist_data[nifty_col].pct_change().loc[pf_returns.index].fillna(0)
    beta, sharpe = calculate_risk_metrics(pf_returns, bm_returns)
    
    # XIRR
    xirr = calculate_xirr(cash_flows, current_pf_val)

    return {
        "dates": dates,
        "invested": invested_capital,
        "portfolio_value": daily_portfolio_value,
        "benchmark_value": daily_benchmark_value,
        "portfolio_profit_pct": pf_profit_pct,
        "benchmark_profit_pct": bm_profit_pct,
        "drawdown": pf_drawdown,
        "metrics": {
            "current_value": current_pf_val,
            "total_invested": current_invested,
            "absolute_profit": current_pf_val - current_invested,
            "absolute_return_pct": (current_pf_val - current_invested) / current_invested * 100 if current_invested > 0 else 0,
            "xirr": xirr,
            "beta": beta,
            "sharpe": sharpe,
            "max_drawdown": pf_max_dd
        }
    }

def get_asset_allocation(holdings, current_prices, selected_symbols=None):
    """Generates data for allocation charts."""
    data = []
    
    for h in holdings:
        if selected_symbols and 'ALL' not in selected_symbols and h['symbol'] not in selected_symbols:
            continue
            
        price = current_prices.get(h['symbol'], h['avg_price'])
        val = h['quantity'] * price
        
        # Risk proxy: Volatility of last 30 days if available, else random
        # In real app, calculate from history.
        
        data.append({
            "symbol": h['symbol'],
            "sector": h.get('sector', 'Other'),
            "value": val,
            "return": (price - h['avg_price']) / h['avg_price'] * 100
        })
        
    return pd.DataFrame(data)