import requests
import logging
import os
import re
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversityRAGClient:
    """Simple RAG client for university queries."""
    
    def __init__(self, rag_endpoint_url: str = None, timeout: int = 60):
        """Initialize RAG client."""
        self.rag_endpoint = rag_endpoint_url or os.getenv(
            "UNIVERSITY_RAG_ENDPOINT", 
            "http://10.45.100.6:8001/chat"
        )
        self.timeout = timeout
        
        logger.info(f"RAG Client initialized with endpoint: {self.rag_endpoint}")
    
    def query_university_info(self, question: str, session_id: str = None) -> str:
        """Query RAG endpoint with user's question."""
        try:
            payload = {
                "user_input": question,
                "session_id": session_id or "default_session"
            }
            logger.info(f"Sending to RAG: {self.rag_endpoint}")
            logger.info(f"Question: '{question}'")
            logger.info(f"Payload: {payload}")

            response = requests.post(
                self.rag_endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"RAG response status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"RAG JSON received: {data}")

                    # Always extract the main answer as a string
                    if isinstance(data, dict):
                        rag_response = (
                            data.get("ai_response") or
                            data.get("response") or 
                            data.get("answer") or 
                            data.get("result") or 
                            data.get("text")
                        )
                        # If the value is a dict, try to get its string value
                        if isinstance(rag_response, dict):
                            rag_response = rag_response.get("ai_response") or rag_response.get("response") or rag_response.get("text") or str(rag_response)
                    else:
                        rag_response = str(data)

                    # If still not a string, fallback to string conversion
                    if not isinstance(rag_response, str):
                        rag_response = str(rag_response)

                    # Remove <think>...</think> blocks
                    formatted_response = re.sub(r"<think>.*?</think>", "", rag_response, flags=re.DOTALL).strip()
                    logger.info(f"Original RAG response: '{rag_response}'")
                    logger.info(f"Formatted response (without thoughts): '{formatted_response}'")

                    # Always return a string
                    return formatted_response

                except Exception as e:
                    logger.error(f"JSON parse error: {e}")
                    return "Sorry, I couldn't understand the university system's response."

            else:
                logger.error(f"RAG failed with status {response.status_code}: {response.text}")
                return f"University system error (status {response.status_code}). Please try again."

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to {self.rag_endpoint}: {e}")
            return "Cannot connect to university information system. Please check your connection."

        except requests.exceptions.Timeout:
            logger.error(f"Timeout after {self.timeout}s")
            return "University system is taking too long to respond. Please try again."

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"Unexpected error: {str(e)}"

    def health_check(self) -> bool:
        """Check if RAG endpoint is responding."""
        try:
            logger.info(f"Health check: {self.rag_endpoint}")
            
            # Simple test query
            test_payload = {"query": "test"}
            response = requests.post(
                self.rag_endpoint, 
                json=test_payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"Health check status: {response.status_code}")
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

# Global instance
rag_client = UniversityRAGClient()