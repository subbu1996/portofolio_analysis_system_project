import logging
from langchain_core.messages import HumanMessage
from src.agent.graph import graph_main_with_persistence as graph

# Configure logging to catch agent errors
logger = logging.getLogger(__name__)

def generate_response(user_input, session_id):
    """
    Interact with the Multi-Agent System (LangGraph).
    
    Args:
        user_input (str): The user's query.
        session_id (str): The current chat session ID for persistence.
        
    Returns:
        tuple: (thinking_process_string, final_response_string)
    """
    #  Map Dash Session ID to LangGraph Thread ID
    config = {"configurable": {"thread_id": session_id}}

    try:
        # Determine the starting point of the conversation
        # need this to filter out old messages and only show "Thinking" for THIS turn.
        initial_state = graph.get_state(config)
        start_msg_count = len(initial_state.values.get("messages", [])) if initial_state.values else 0

        # Invoke the Multi-Agent System
        # pass the user input as a HumanMessage. 
        # The graph handles routing (Supervisor -> Worker -> Supervisor)
        response_state = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config
        )

        # Extract and Parse New Messages
        all_messages = response_state.get("messages", [])
        new_messages = all_messages[start_msg_count:]

        thinking_lines = []
        final_response = "I processed the request but returned no output."

        # Filter specifically for AI messages to construct the response
        ai_messages = [m for m in new_messages if m.type == "ai"]
        
        if ai_messages:
            # CONVENTION: The LAST message from the system is the response to the user.
            # (Usually from the 'supervisor' summarizing the results)
            final_message = ai_messages[-1]
            final_response = final_message.content

            # ALL PREVIOUS messages in this turn are considered "Thinking Process"
            # (e.g., Portfolio Agent calculating XIRR, News Agent fetching data)
            for m in new_messages:
                # Skip the final message and the user input
                if m == final_message or m.type == "human":
                    continue
                
                # Format Tool Outputs
                if m.type == "tool":
                    # We summarize tool outputs to avoid cluttering the UI with raw JSON
                    tool_name = getattr(m, "name", "Tool")
                    thinking_lines.append(f"**[System Ops]**: Executed `{tool_name}` successfully.")
                
                # Format Worker Agent Thoughts
                elif m.type == "ai":
                    sender = getattr(m, "name", "Agent")
                    # Clean up the sender name for display
                    display_name = sender.replace("_", " ").title()
                    thinking_lines.append(f"**[{display_name}]**: {m.content}")

        # Join thinking lines with newlines for the Markdown renderer
        thinking_content = "\n\n".join(thinking_lines) if thinking_lines else None
        
        return thinking_content, final_response

    except Exception as e:
        logger.error(f"Error in Multi-Agent invocation: {e}", exc_info=True)
        # Graceful error handling for the UI
        return None, f"**System Error**: I encountered an issue while coordinating the agents. \n\n*Debug Details*: {str(e)}"