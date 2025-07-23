import json
from utils.rag_client import rag_client

# Load mock data if needed
try:
    with open("conf/mock.json", "r") as file:
        MOCK_DATA = json.load(file)
except FileNotFoundError:
    MOCK_DATA = {"default_response": "I'm here to help with university information."}


def collect_name(llm, state, user_input=None):
    """Collect user's name - entry point"""
    if user_input:
        # User provided their name
        state["name"] = user_input.strip()
        state["current_node"] = "university_chat"
        state["next_question"] = f"Nice to meet you, {state['name']}! I'm your university assistant. How can I help you today?"
        
        # Add to history
        if "history" not in state:
            state["history"] = []
        state["history"].append({"user": user_input, "assistant": state["next_question"]})
        
        return state
    else:
        # Initial greeting
        state["current_node"] = "collect_name"
        state["next_question"] = "Hello! I'm your university assistant. What's your name?"
        return state


def university_chat(llm, state, user_input=None):
    """Handle all university-related questions using RAG"""
    if not user_input:
        return state
    
    user_input = user_input.strip().lower()
    
    # Check for goodbye intent
    goodbye_phrases = ["bye", "goodbye", "see you", "thanks", "thank you", "exit", "quit"]
    if any(phrase in user_input for phrase in goodbye_phrases):
        state["current_node"] = "goodbye"
        return state
    
    # Use RAG for all other questions
    try:
        session_id = state.get("session_id", "default")
        rag_response = rag_client.query_university_info(user_input, session_id=session_id)
        
        if rag_response and rag_response.strip():
            state["next_question"] = rag_response
        else:
            state["next_question"] = "I'm sorry, I don't have information about that. Could you please rephrase your question or ask about admissions, courses, campus facilities, or other university services?"
            
    except Exception as e:
        print(f"RAG query failed: {e}")
        state["next_question"] = "I'm having trouble accessing the university information system right now. Please try again in a moment."
    
    # Add to history
    if "history" not in state:
        state["history"] = []
    state["history"].append({"user": user_input, "assistant": state["next_question"]})
    
    # Stay in chat mode
    state["current_node"] = "university_chat"
    return state


def goodbye(llm, state, user_input=None):
    """Handle goodbye and end conversation"""
    name = state.get("name", "there")
    
    goodbye_messages = [
        f"Goodbye, {name}! Feel free to come back if you have more questions about our university.",
        f"Thank you for visiting, {name}! Have a great day!",
        f"See you later, {name}! Good luck with your university journey!",
        f"Take care, {name}! I'm here whenever you need university information."
    ]
    
    # Pick a goodbye message (you could make this random)
    state["next_question"] = goodbye_messages[0]
    state["conversation_ended"] = True
    state["current_node"] = "goodbye"
    
    # Add to history
    if "history" not in state:
        state["history"] = []
    state["history"].append({"assistant": state["next_question"]})
    
    # Clear RAG session context
    try:
        session_id = state.get("session_id")
        if session_id:
            rag_client.clear_session_context(session_id)
    except Exception as e:
        print(f"Failed to clear RAG context: {e}")
    
    return state


# Minimal helper functions if needed
def get_user_context(state):
    """Get user context for personalized responses"""
    return {
        "name": state.get("name"),
        "history_count": len(state.get("history", [])),
        "session_id": state.get("session_id")
    }


def format_university_response(response, user_name=None):
    """Format RAG responses in a friendly way"""
    if not response:
        return "I don't have information about that topic."
    
    # Add personal touch if name is available
    if user_name and not response.startswith(user_name):
        return f"{response}"
    
    return response