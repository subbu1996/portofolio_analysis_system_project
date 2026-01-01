import logging

from src.agent.portfolio_agent import create_portfolio_agent
from src.agent.supervisor_agent import create_supervisor_agent

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
logger.info("Successfully Imported Environmental Variable")

def create_multi_agent_system():
    """Create the complete multi-agent system.
    
    Returns:
        Compiled supervisor graph with all agents
    """
    # logger.info("Initializing Multi-Agent Portfolio System...")
    
    # Create worker agents
    portfolio_agent = create_portfolio_agent()
    
    # Agents - WiP
    # news_agent = create_news_agent()
    # monitor_agent = create_monitor_agent()
    # synthesis_agent = create_synthesis_agent()
    # dashboards_agent = create_dashboards_agent()
    
    # Create supervisor with all agents
    supervisor_graph = create_supervisor_agent(
        agents=[portfolio_agent]
    )
    
    # Compile the graph
    compiled_graph = supervisor_graph.compile()
    
    # logger.info("Multi-Agent System initialized successfully")
    return compiled_graph

graph = create_multi_agent_system()