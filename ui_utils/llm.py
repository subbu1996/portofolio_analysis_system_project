import logging
from langchain_core.messages import HumanMessage
from src.agent.graph import graph_main_with_persistence as graph
import threading
from queue import Queue, Empty
from ui_utils.db import add_message, update_message_content

# Configure logging
logger = logging.getLogger(__name__)

# Global state management
streaming_states = {}
streaming_lock = threading.Lock()

class StreamingState:
    """Manages the state of a streaming response"""
    
    def __init__(self, session_id):
        # FIX: Ensure session_id is always a string for consistency
        self.session_id = str(session_id)
        self.thinking_chunks = []
        self.response_chunks = []
        self.status = "processing"
        self.error_message = None
        self.message_id = None
        self.should_stop = False
        
    def add_thinking(self, chunk):
        self.thinking_chunks.append(chunk)
        
    def add_response(self, chunk):
        self.response_chunks.append(chunk)
        
    def get_thinking(self):
        return "\n\n".join(self.thinking_chunks) if self.thinking_chunks else None
        
    def get_response(self):
        return "".join(self.response_chunks) if self.response_chunks else ""
        
    def mark_complete(self):
        self.status = "complete"
        
    def mark_error(self, error_msg):
        self.status = "error"
        self.error_message = error_msg

    def mark_stopped(self):
        self.status = "stopped"
        self.should_stop = True

    def is_active(self):
        return self.status == "processing" and not self.should_stop


def get_streaming_state(session_id):
    """Get the current streaming state for a session"""
    # FIX: Cast key to string
    key = str(session_id)
    with streaming_lock:
        return streaming_states.get(key)


def clear_streaming_state(session_id):
    """Clear the streaming state after completion"""
    # FIX: Cast key to string
    key = str(session_id)
    with streaming_lock:
        if key in streaming_states:
            del streaming_states[key]

def stop_streaming(session_id):
    """Stop the streaming for a session"""
    # FIX: Cast key to string
    key = str(session_id)
    with streaming_lock:
        state = streaming_states.get(key)
        if state:
            state.mark_stopped()
            logger.info(f"Streaming stopped for session {key}")
            return True
    return False


def _get_message_identifier(msg):
    """
    Generate a unique identifier for a message to check for duplicates.
    Prioritizes message ID, falls back to (type, content) hash.
    """
    if hasattr(msg, 'id') and msg.id:
        return msg.id
    # Fallback for messages without IDs (uses type and content)
    return f"{msg.type}:{msg.content}"


def _process_stream_chunk(chunk, state, seen_ids):
    """Process a single chunk from the LangGraph stream"""
    if state.should_stop:
        return
    
    for node_name, node_output in chunk.items():
        if "messages" in node_output:
            messages = node_output["messages"]
            for msg in messages:
                if state.should_stop:  
                    return
                
                msg_id = _get_message_identifier(msg)
                if msg_id in seen_ids:
                    continue
                  
                if msg.type == "ai":
                    sender = getattr(msg, "name", node_name)
                    is_final = sender.lower() in ["supervisor", ""] or not hasattr(msg, "name")
                    
                    if is_final:
                        if hasattr(msg, 'content') and msg.content:
                            state.add_response(msg.content)
                    else:
                        display_name = sender.replace("_", " ").title()
                        state.add_thinking(f"**[{display_name}]**: {msg.content}")
                
                elif msg.type == "tool":
                    tool_name = getattr(msg, "name", "Tool")
                    state.add_thinking(f"**[System Ops]**: Executed `{tool_name}` successfully.")


def _stream_response_worker(user_input, session_id, state):
    """Worker thread that processes the LLM stream"""
    config = {"configurable": {"thread_id": str(session_id)}}
    
    try:
        initial_state = graph.get_state(config)
        
        seen_ids = set()
        if initial_state.values and "messages" in initial_state.values:
            for m in initial_state.values["messages"]:
                seen_ids.add(_get_message_identifier(m))
        
        # Create placeholder
        thinking_preview = "Processing your request..."
        response_preview = ""
        message_id = add_message(
            session_id, 
            "assistant", 
            response_preview,
            thinking_process=thinking_preview
        )
        state.message_id = message_id
        
        # Stream
        for chunk in graph.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
            stream_mode="updates"
        ):
            _process_stream_chunk(chunk, state, seen_ids)
            
            # Update DB periodically
            if len(state.response_chunks) % 3 == 0 or len(state.thinking_chunks) > 0:
                 update_message_content(
                    message_id,
                    state.get_response() or "...",
                    state.get_thinking()
                )
        
        # Final update
        final_response = state.get_response() or "I processed the request but returned no output."
        final_thinking = state.get_thinking()
        
        update_message_content(message_id, final_response, final_thinking)
        state.mark_complete()
        
    except Exception as e:
        logger.error(f"Error in streaming response: {e}", exc_info=True)
        error_msg = f"**System Error**: I encountered an issue while processing your request.\n\n*Debug Details*: {str(e)}"
        state.mark_error(error_msg)
        if state.message_id:
            update_message_content(state.message_id, error_msg, None)


def start_streaming_response(user_input, session_id):
    """Start generating a streaming response"""
    session_id = str(session_id)
    
    clear_streaming_state(session_id)
    state = StreamingState(session_id)
    
    with streaming_lock:
        streaming_states[session_id] = state
    
    thread = threading.Thread(
        target=_stream_response_worker,
        args=(user_input, session_id, state),
        daemon=True
    )
    thread.start()
    
    return state