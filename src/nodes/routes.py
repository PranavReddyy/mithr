from pprint import pprint as pp
from langgraph.graph import END
import json

from utils.tts import botspeak


def collect_name_router(state):
    """Route from name collection to university chat."""
    if state.get("collect_name_result") is None:
        return "collect_name"
    return "university_chat"


def university_chat_router(state):
    """Route for university chat - continues conversation or ends."""
    # Check if user wants to end conversation
    last_query = state.get("last_query", "").lower()
    
    # Keywords that indicate user wants to end conversation
    goodbye_keywords = ["goodbye", "bye", "exit", "quit", "end", "stop", "thanks", "thank you"]
    
    if any(keyword in last_query for keyword in goodbye_keywords):
        return "goodbye"
    
    # Continue university chat
    return "university_chat"


def goodbye_router(state):
    """Final node - ends conversation."""
    return END
