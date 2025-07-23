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
    conversation_ended: bool