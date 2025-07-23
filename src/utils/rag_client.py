import requests
import asyncio
import aiohttp
import logging
from typing import Dict, Optional
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UniversityRAGClient:
    """Client for university RAG (Retrieval-Augmented Generation) system."""
    
    def __init__(self, rag_endpoint_url: str = None, timeout: int = 15):
        """
        Initialize RAG client.
        
        Args:
            rag_endpoint_url (str): URL of your RAG endpoint
            timeout (int): Request timeout in seconds
        """
        # Use environment variable or provided URL
        self.rag_endpoint = rag_endpoint_url or os.getenv("UNIVERSITY_RAG_ENDPOINT", "http://localhost:8000/query")
        self.timeout = timeout
        self.session_context = {}
        
        logger.info(f"RAG Client initialized with endpoint: {self.rag_endpoint}")

    def query_university_info(self, question: str, session_id: str = None, context: Dict = None) -> str:
        """
        Synchronous query to RAG endpoint.
        
        Args:
            question (str): User's question
            session_id (str): Session identifier for context
            context (Dict): Additional context information
            
        Returns:
            str: RAG response
        """
        try:
            # Prepare request payload
            payload = {
                "query": question,
                "question": question,  # Some RAG systems use 'question' instead of 'query'
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add context if provided
            if context:
                payload["context"] = context
            
            # Add session context if available
            if session_id and session_id in self.session_context:
                payload["conversation_history"] = self.session_context[session_id]
            
            logger.info(f"Sending query to RAG: {question[:100]}...")
            
            response = requests.post(
                self.rag_endpoint,
                json=payload,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "University-Assistant/1.0"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, dict):
                    # Try different possible response keys
                    rag_response = (
                        data.get("response") or 
                        data.get("answer") or 
                        data.get("result") or 
                        data.get("text") or
                        str(data)
                    )
                else:
                    rag_response = str(data)
                
                # Update session context
                if session_id:
                    if session_id not in self.session_context:
                        self.session_context[session_id] = []
                    
                    self.session_context[session_id].append({
                        "question": question,
                        "response": rag_response,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Keep only last 10 exchanges to manage memory
                    if len(self.session_context[session_id]) > 10:
                        self.session_context[session_id] = self.session_context[session_id][-10:]
                
                logger.info(f"RAG response received: {rag_response[:100]}...")
                return rag_response
                
            else:
                logger.error(f"RAG endpoint returned status {response.status_code}: {response.text}")
                return self._get_fallback_response(question)
                
        except requests.exceptions.ConnectException:
            logger.error("Cannot connect to RAG endpoint - is it running?")
            return "I'm sorry, I cannot connect to the university information system right now. Please check if the system is running and try again."
            
        except requests.exceptions.Timeout:
            logger.error("RAG endpoint timeout")
            return "The university information system is taking too long to respond. Please try asking a simpler question or try again later."
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return self._get_fallback_response(question)

    async def async_query_university_info(self, question: str, session_id: str = None, context: Dict = None) -> str:
        """
        Asynchronous query to RAG endpoint.
        
        Args:
            question (str): User's question
            session_id (str): Session identifier
            context (Dict): Additional context
            
        Returns:
            str: RAG response
        """
        try:
            payload = {
                "query": question,
                "question": question,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            if context:
                payload["context"] = context
            
            if session_id and session_id in self.session_context:
                payload["conversation_history"] = self.session_context[session_id]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rag_endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        if isinstance(data, dict):
                            rag_response = (
                                data.get("response") or 
                                data.get("answer") or 
                                data.get("result") or 
                                str(data)
                            )
                        else:
                            rag_response = str(data)
                        
                        return rag_response
                    else:
                        logger.error(f"Async RAG endpoint returned status {response.status}")
                        return self._get_fallback_response(question)
                        
        except Exception as e:
            logger.error(f"Async RAG query failed: {e}")
            return self._get_fallback_response(question)

    def _get_fallback_response(self, question: str) -> str:
        """Generate fallback response when RAG is unavailable."""
        question_lower = question.lower()
        
        # Simple keyword-based fallback responses
        if any(word in question_lower for word in ["admission", "apply", "application"]):
            return "For admission information, please visit the admissions office or check the university website. I'm currently unable to access the detailed admission database."
            
        elif any(word in question_lower for word in ["course", "subject", "curriculum"]):
            return "For course information, please contact the academic office or your department advisor. I'm having trouble accessing the course catalog right now."
            
        elif any(word in question_lower for word in ["fee", "payment", "cost", "tuition"]):
            return "For fee and payment information, please contact the finance office or check your student portal. I cannot access fee details at the moment."
            
        elif any(word in question_lower for word in ["library", "book", "resource"]):
            return "For library resources, please visit the university library or use the online catalog. I'm currently unable to access library information."
            
        else:
            return "I'm sorry, I'm having trouble accessing the university information system right now. Please try asking again later, or contact the relevant university office directly for assistance."

    def clear_session_context(self, session_id: str):
        """Clear context for a specific session."""
        if session_id in self.session_context:
            del self.session_context[session_id]
            logger.info(f"Cleared context for session: {session_id}")

    def health_check(self) -> bool:
        """Check if RAG endpoint is healthy."""
        try:
            response = requests.get(f"{self.rag_endpoint}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


# Global RAG client instance
rag_client = UniversityRAGClient()

def call_rag_endpoint(query: str, session_id: str = None) -> str:
    """Simple function to call RAG endpoint (backward compatibility)."""
    return rag_client.query_university_info(query, session_id)