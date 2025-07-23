from uuid import uuid4
from typing import Any, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The in-memory session store (using string keys for consistency)
session_store: Dict[str, Any] = {}


def create_session(state: Any) -> str:
    """
    Create a new session with a unique ID.
    
    Args:
        state: Initial state for the session
        
    Returns:
        str: Session ID
    """
    session_id = str(uuid4())
    state['session_id'] = session_id
    session_store[session_id] = state
    logger.info(f"Created session: {session_id}")
    return session_id


def get_session(session_id: str) -> Optional[Any]:
    """
    Get session by ID.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Optional[Any]: Session state or None if not found
    """
    session = session_store.get(session_id)
    if session:
        logger.debug(f"Retrieved session: {session_id}")
    else:
        logger.warning(f"Session not found: {session_id}")
    return session


def get_all_sessions() -> Dict[str, Any]:
    """
    Get all active sessions.
    
    Returns:
        Dict[str, Any]: Dictionary of all sessions
    """
    logger.info(f"Retrieved all sessions: {len(session_store)} active")
    return session_store.copy()


def update_session(session_id: str, new_state: Any) -> bool:
    """
    Update session state.
    
    Args:
        session_id: Session identifier
        new_state: New state to update
        
    Returns:
        bool: True if successful, False if session not found
    """
    if session_id in session_store:
        session_store[session_id] = new_state
        logger.debug(f"Updated session: {session_id}")
        return True
    logger.warning(f"Failed to update session: {session_id} not found")
    return False


def delete_session(session_id: str) -> bool:
    """
    Delete a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        bool: True if successful, False if session not found
    """
    if session_id in session_store:
        del session_store[session_id]
        logger.info(f"Deleted session: {session_id}")
        return True
    logger.warning(f"Failed to delete session: {session_id} not found")
    return False


def clear_all_sessions():
    """Clear all sessions (useful for testing/cleanup)."""
    session_count = len(session_store)
    session_store.clear()
    logger.info(f"Cleared all sessions: {session_count} sessions removed")


def get_session_count() -> int:
    """Get total number of active sessions."""
    return len(session_store)


def get_sessions_by_node(node_name: str) -> Dict[str, Any]:
    """
    Get all sessions currently at a specific node.
    
    Args:
        node_name: Name of the node
        
    Returns:
        Dict[str, Any]: Sessions at the specified node
    """
    filtered_sessions = {
        session_id: session_data 
        for session_id, session_data in session_store.items()
        if session_data.get("current_node") == node_name
    }
    logger.debug(f"Found {len(filtered_sessions)} sessions at node: {node_name}")
    return filtered_sessions