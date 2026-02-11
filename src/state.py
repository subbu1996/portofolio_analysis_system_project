"""State management for the multi-agent portfolio system."""
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the multi-agent system.
    
    Attributes:
        messages: List of conversation messages
        next: Name of the next agent to call or 'FINISH'
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str
    # portfolio_data: dict | None
    # analysis_results: dict | None
    remaining_steps: list | None
    # error: str | None


class PortfolioSchema(TypedDict):
    """Schema for portfolio data structure.
    
    Supports Indian stocks (NSE/BSE) and mutual funds.
    """
    holdings: list[dict]  # List of current holdings
    transactions: list[dict]  # Historical transactions
    watch_list: list[str]  # Stocks/MFs to watch
    start_date: str  # Portfolio start date
    net_value: float  # Current portfolio value


class HoldingSchema(TypedDict):
    """Schema for individual holding."""
    symbol: str  # Stock symbol (e.g., "RELIANCE.NSE", "TCS.BSE")
    asset_type: str  # "equity" or "mutual_fund"
    quantity: float
    avg_price: float
    current_price: float
    platform_acquired: str
    purchase_date: str
    sector: str | None


class TransactionSchema(TypedDict):
    """Schema for transaction records."""
    date: str
    symbol: str
    transaction_type: str  # "buy" or "sell"
    quantity: float
    price: float
    charges: float

class Portfolio(TypedDict):
    """Complete portfolio schema."""
    user_id: str
    holdings: list[HoldingSchema]
    transactions: list[TransactionSchema]
    watch_list: list[str]
    start_date: str
    net_value: float
    currency: Literal["INR"]


class AnalysisResult(TypedDict):
    """Results from financial analysis."""
    xirr: float | None
    cagr: float | None
    total_invested: float
    current_value: float
    total_gains: float
    realized_gains: float
    unrealized_gains: float
    sector_exposure: dict[str, float]
    asset_class_exposure: dict[str, float]
    rolling_returns: dict[str, float]
