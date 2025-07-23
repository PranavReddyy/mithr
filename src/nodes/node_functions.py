from langchain_core.messages import AIMessage, HumanMessage
import requests
from utils.tts import botspeak
from session_store import delete_session  
from models.userstate import State
from utils.rag_client import call_rag_endpoint


def handle_node_entry(state: State, node_name: str) -> State:
    """Handle entering a new node in the workflow."""
    if state.get("current_node") != node_name:
        return {**state, "retry_count": 0, "current_node": node_name}
    return state


def collect_name(llm, state, user_input=None):  # Keep llm param for compatibility but don't use it
    """Collect user's name for personalized interaction."""
    state = handle_node_entry(state, "collect_name")
    history = state.get("history", [])
    
    if not user_input:
        question = "Hello! I'm your university assistant. What's your name?"
        botspeak(question)
        history.append(AIMessage(content=question))
        return {**state, "next_question": question, "history": history}
    
    history.append(HumanMessage(content=user_input))
    
    # Simple name extraction - NO LLM NEEDED
    name = user_input.strip()
    if len(name) < 2:
        question = "Could you please provide your full name?"
        botspeak(question)
        history.append(AIMessage(content=question))
        return {**state, "next_question": question, "history": history}
    
    return {
        **state, 
        "name": name, 
        "collect_name_result": name,
        "history": history
    }


def university_chat(llm, state, user_input=None):  # Keep llm param for compatibility but don't use it
    """Handle general university-related queries using RAG ONLY."""
    state = handle_node_entry(state, "university_chat")
    history = state.get("history", [])
    name = state.get("name", "there")
    
    if not user_input:
        question = f"Hi {name}! How can I help you with university-related questions today?"
        botspeak(question)
        history.append(AIMessage(content=question))
        return {**state, "next_question": question, "history": history}
    
    history.append(HumanMessage(content=user_input))
    
    # Call RAG endpoint DIRECTLY - NO LLM
    try:
        session_id = state.get("session_id")
        rag_response = call_rag_endpoint(user_input, session_id)
        
        # Use RAG response directly
        response = rag_response
        
        botspeak(response)
        history.append(AIMessage(content=response))
        
        return {
            **state, 
            "next_question": response,
            "history": history,
            "last_query": user_input
        }
    except Exception as e:
        error_response = "I'm sorry, I'm having trouble accessing the university information right now. Could you try asking again?"
        botspeak(error_response)
        history.append(AIMessage(content=error_response))
        return {**state, "next_question": error_response, "history": history}


def goodbye(llm, state, user_input=None):  # Keep llm param for compatibility but don't use it
    """Handle conversation ending."""
    state = handle_node_entry(state, "goodbye")
    history = state.get("history", [])
    name = state.get("name", "")
    
    goodbye_message = f"Thank you for using the university assistant, {name}! Have a great day!"
    botspeak(goodbye_message)
    history.append(AIMessage(content=goodbye_message))
    
    # Clean up session
    session_id = state.get("session_id")
    if session_id:
        delete_session(session_id)
    
    return {
        **state, 
        "next_question": goodbye_message,
        "history": history,
        "conversation_ended": True
    }