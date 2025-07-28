from utils.rag_client import rag_client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def direct_rag_query(user_input, session_id=None):
    """Direct RAG query - no nodes, no routing, just RAG"""
    logger.info(f"direct_rag_query called with user_input: '{user_input}', session_id: {session_id}")
    
    if not user_input or not user_input.strip():
        logger.info("Empty user input, returning greeting")
        return "Hello! I'm your university assistant. How can I help you today?"
    
    try:
        logger.info(f"Calling rag_client.query_university_info with: '{user_input.strip()}'")
        
        # Send directly to RAG
        response = rag_client.query_university_info(user_input.strip(), session_id=session_id)
        
        logger.info(f"RAG client returned: '{response[:100] if response else 'None'}...'")
        
        if response and response.strip():
            return response
        else:
            logger.warning("RAG returned empty response")
            return "I'm sorry, I don't have information about that. Could you please rephrase your question?"
            
    except Exception as e:
        logger.error(f"RAG query failed with exception: {e}")
        print(f"RAG query failed: {e}")
        return "I'm having trouble accessing the university information system right now. Please try again in a moment."