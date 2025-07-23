from typing_extensions import TypedDict
from typing import Optional, List, Dict, Any


class State(TypedDict):
    # User information
    name: Optional[str]
    
    # Conversation flow
    current_node: Optional[str]
    next_question: Optional[str]
    last_query: Optional[str]
    
    # Session management
    session_id: Optional[str]
    history: List[Dict[str, Any]]
    retry_count: int
    
    # University assistant specific
    conversation_ended: bool
    
    # Optional fields for extension
    user_context: Optional[Dict[str, Any]]  # For storing additional user context
    rag_context: Optional[Dict[str, Any]]   # For RAG-specific context