import logging
from langgraph_supervisor import create_supervisor
from state import AgentState
from agent.create_llm import create_ollama_llm

logger = logging.getLogger(__name__)


def create_supervisor_agent(agents: list):
    """Create the Supervisor Agent using langgraph_supervisor.
    
    This central planning agent:
    - Receives user queries
    - Reasons about which agent(s) to delegate tasks to
    - Orchestrates multi-step workflows
    - Synthesizes final responses
    
    Args:
        agents: List of worker agents to supervise
        
    Returns:
        Compiled supervisor graph
    """
    
    llm = create_ollama_llm()
    
    supervisor = create_supervisor(
        agents=agents,
        model=llm,
        prompt=(
            "You are an AI Supervisor and Planning agent managing a portfolio analysis system for Indian stocks and mutual funds.\n\n"

            "YOUR ROLE:\n"
            "- Understand user queries about portfolio management\n"
            "- Delegate tasks to specialized agents\n"
            "- Synthesize results into clear, actionable responses\n"
            "- Provide final answers directly to users\n\n"

            "AVAILABLE AGENTS:\n"
            "- portfolio_agent (The Quant): Handles all financial calculations, market data fetching, "
            "and portfolio analysis. Use for: XIRR/CAGR calculations, P&L analysis, exposure breakdown, "
            "market data queries, watch list analysis\n\n"

            "FUTURE AGENTS (not yet available):\n"
            "- news_agent: For market news and sentiment analysis\n"
            "- monitor_agent: For portfolio monitoring and alerts\n"
            "- synthesis_agent: For comprehensive report generation\n"
            "- dashboards_agent: For visualization requests\n\n"

            "WORKFLOW:\n"
            "1. Analyze the user's request carefully\n"
            "2. Reason & plan the next tasks carefully\n"
            "3. Determine which agent(s) can help\n"
            "4. Delegate specific sub-tasks clearly\n"
            "5. Review agent responses\n"
            "6. Provide a synthesized, user-friendly answer\n\n"

            "BEST PRACTICES:\n"
            "- Delegate ONE task at a time (no parallel calls)\n"
            "- Be specific in your delegation instructions\n"
            "- Show your reasoning process to the user\n"
            "- If portfolio data is needed, ask the portfolio_agent to parse it first\n"
            "- Format numbers clearly (with INR currency for Indian markets)\n"
            "- Provide context and insights, not just raw numbers\n\n"
            "IMPORTANT:\n"
            "- You are a planner and coordinator, NOT an executor\n"
            "- Always delegate work to agents - do not calculate yourself\n"
            "- For any portfolio analysis, use portfolio_agent\n"
            "- Be transparent about your reasoning and planning steps\n"
        ),
        state_schema=AgentState,
        add_handoff_back_messages=True,
        output_mode="full_history",
        parallel_tool_calls=False,  # Process one agent at a time
        supervisor_name="supervisor",
    )
    
    # logger.info("Supervisor Agent created successfully")
    return supervisor



