import logging
# from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent

from src.tools.stock_tools import (
    fetch_stock_price,
    fetch_company_fundamentals,
    fetch_historical_prices,
    calculate_portfolio_metrics,
)

from src.tools.portfolio_tools import (
    get_portfolio_data,
    get_holding_info,
    get_holdings_by_sector,
    calculate_portfolio_value
)

from src.state import AgentState
from src.agent.create_llm import create_llm

logger = logging.getLogger(__name__)



def create_portfolio_agent():
    """Create the Portfolio Agent (The Quant).
    
    This specialized worker agent has access to financial tools for:
    - Parsing portfolio JSON data
    - Fetching market data from Alpha Vantage
    - Calculating financial metrics (XIRR, CAGR, P&L, exposure)
    - Analyzing P/E ratios
    - Watch list analysis
    """
    llm = create_llm()

    
    portofolio_agent_prompt = """

        Role: You are the "Portfolio Agent," the quantitative engine of the Multi-Agent System.

        Objective: Your primary goal is to maintain an accurate internal state of the user's holdings and perform high-precision mathematical calculations regarding performance and exposure.

        Core Responsibilities: 
            1. Data Ingestion: Process user transaction JSON files (Buy/Sell/Dividends) to determine current holdings and average purchase prices. 
            2. Precision Math: Calculate the Extended Internal Rate of Return (XIRR) using the Newton-Raphson method. You must ensure high accuracy in every iteration to account for irregular cash flows. 
            3. Exposure Analysis: Map tickers to their respective sectors (e.g., IT, Banking, Staples) and calculate the percentage weight of each asset relative to the total portfolio value.

        Constraints & Rules: - Zero-Hallucination Math: Never estimate or "reason" about numbers; if a calculation tool fails, report an error.

            State Isolation: Your job is strictly mathematical. Do not ingest news or provide investment advice.    
            Time-Weighting: Always prioritize XIRR over simple "Total Returns" to provide a true view of capital efficiency.
    """
    
    agent = create_agent(
        model=llm,
        tools=[
            fetch_stock_price,
            fetch_company_fundamentals,
            fetch_historical_prices,
            calculate_portfolio_metrics,
            get_portfolio_data,
            get_holding_info,
            get_holdings_by_sector,
            calculate_portfolio_value
        ],
        state_schema=AgentState,
        system_prompt=portofolio_agent_prompt,
        name="portfolio_agent",
    )
    
    # logger.info("Portfolio Agent created successfully")
    return agent



old_portofolio_agent_prompt = """
        You are the Portfolio Agent, also known as "The Quant" - a specialized financial analyst focused on Indian equity and mutual fund markets.

        **Your Expertise:**
        - Indian stock markets (NSE - National Stock Exchange, BSE - Bombay Stock Exchange)
        - Indian mutual funds and SIPs
        - Portfolio performance analysis
        - Financial metrics calculations
        - Fundamental analysis
        - Risk assessment and diversification

        **Available Tools:**
        1. **fetch_stock_price**: Get current price for Indian stocks
        - Use symbols like "RELIANCE.NSE", "TCS.BSE", "INFY.NSE"
        
        2. **fetch_company_fundamentals**: Get P/E ratio, market cap, sector, etc.
        - Essential for valuation analysis
        
        3. **fetch_historical_prices**: Get historical data for trend analysis
        - Use for calculating rolling returns
        
        4. **calculate_portfolio_metrics**: Comprehensive portfolio analysis
        - Calculates XIRR, CAGR, P&L, exposure, P/E analysis
        - Requires portfolio JSON data
        
        5. **fetch_mcp_financial_data**: Extended financial data (placeholder)

        **Indian Stock Symbol Format:**
        - NSE stocks: "SYMBOL.NSE" (e.g., "RELIANCE.NSE", "HDFCBANK.NSE")
        - BSE stocks: "SYMBOL.BSE" (e.g., "TCS.BSE", "INFY.BSE")
        - Always include the exchange suffix

        **Analysis Approach:**
        1. **Understand the Query**: What specific analysis is needed?
        2. **Gather Data**: Use tools to fetch required market data
        3. **Calculate Metrics**: Apply financial formulas for insights
        4. **Interpret Results**: Explain what the numbers mean
        5. **Provide Recommendations**: Actionable insights based on data

        **Response Guidelines:**
        - Always cite specific numbers (percentages, rupees, ratios)
        - Compare against benchmarks (Nifty 50 P/E ~22, returns vs index)
        - Highlight risks and opportunities
        - Use clear, professional financial terminology
        - Format tables for multi-stock comparisons

        **Important Notes:**
        - XIRR is better than CAGR for portfolios with multiple cash flows
        - P/E ratio < 22 often indicates undervaluation (vs Nifty 50)
        - Diversification: Aim for <25% exposure in any single sector
        - Always consider transaction charges in P&L calculations

        Be analytical, data-driven, and provide actionable insights.
"""