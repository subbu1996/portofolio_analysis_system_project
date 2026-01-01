"""Main entry point for the portfolio management system."""
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from agent.graph import create_multi_agent_system
from utils import load_portfolio_from_file, pretty_print_messages


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Successfully Imported Environmental Variable")


def run_portfolio_analysis(query: str, portfolio_data: dict = None):
    """Run portfolio analysis with the multi-agent system.
    
    Args:
        query: User query string
        portfolio_data: Optional portfolio data dictionary
    """
    # logger.info("Starting Portfolio Analysis...")
    
    # Create the multi-agent system
    app = create_multi_agent_system()
    
    # Prepare the input
    input_data = {
        "messages": [HumanMessage(content=query)],
        "next": "",
        "portfolio_data": portfolio_data,
        "analysis_results": None
    }
    
    print(f"\n{'='*80}")
    print(f"USER QUERY: {query}")
    print(f"{'='*80}\n")
    
    # Stream the execution
    try:
        for update in app.stream(input_data, stream_mode="updates"):
            # print(update)
            pretty_print_messages(update)
        
        # logger.info("Portfolio analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        raise


def run_examples():
    """Run example queries demonstrating system capabilities."""
    
    # Load sample portfolio
    portfolio_data = load_portfolio_from_file()
    portfolio_json = json.dumps(portfolio_data)
    
    examples = [
        {
            "name": "Portfolio Overview",
            "query": f"Analyze this portfolio and provide comprehensive metrics: {portfolio_json}"
        },
        {
            "name": "P/E Ratio Analysis",
            "query": f"Calculate the weighted P/E ratio for my portfolio: {portfolio_json}"
        },
        {
            "name": "Watch List Analysis",
            "query": "Analyze these stocks for me: RELIANCE, TCS, HDFCBANK"
        },
        {
            "name": "Market Data",
            "query": "Get me the current price and fundamentals for TCS on NSE"
        },
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n\n{'#'*80}")
        print(f"EXAMPLE {i}: {example['name']}")
        print(f"{'#'*80}\n")
        
        run_portfolio_analysis(example["query"], portfolio_data)
        
        print("\n" + "="*80 + "\n")


def interactive_mode():
    """Run in interactive mode for custom queries."""
    
    print("\n" + "="*80)
    print("PORTFOLIO AGENT - INTERACTIVE MODE")
    print("="*80)
    print("\nCommands:")
    print("  - Type your query to analyze portfolio")
    print("  - Type 'load' to load portfolio data")
    print("  - Type 'exit' to quit")
    print("\n" + "="*80 + "\n")
    
    portfolio_data = None
    
    while True:
        try:
            user_input = input("\n You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Goodbye!")
                break
            
            if user_input.lower() == 'load':
                portfolio_data = load_portfolio_from_file()
                print("Portfolio data loaded successfully")
                continue
            
            if not user_input:
                continue
            
            # If query mentions "portfolio" or "my holdings", include portfolio data
            if portfolio_data and any(keyword in user_input.lower() 
                                     for keyword in ['portfolio', 'holdings', 'my', 'calculate']):
                portfolio_json = json.dumps(portfolio_data)
                user_input = f"{user_input}\n\nPortfolio data: {portfolio_json}"
            
            run_portfolio_analysis(user_input, portfolio_data)
            
        except KeyboardInterrupt:
            print("\n\n Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\n Error: {e}\n")


def main():
    """Main entry point."""
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "examples":
            run_examples()
        elif sys.argv[1] == "interactive":
            interactive_mode()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python main.py [examples|interactive]")
    else:
        # Default to interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()

