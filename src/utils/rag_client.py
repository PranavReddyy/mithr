import requests
import logging
import os
from typing import Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversityRAGClient:
    """RAG client for university queries (new API)."""

    def __init__(self, rag_endpoint_url: str = None, timeout: int = 60):
        self.rag_endpoint = rag_endpoint_url or os.getenv(
            "UNIVERSITY_RAG_ENDPOINT",
            "http://10.45.100.6:8005/chat"
        )
        self.timeout = timeout
        logger.info(f"RAG Client initialized with endpoint: {self.rag_endpoint}")

    def query_university_info(
        self, question: str, session_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Query RAG endpoint with user's question.
        Returns dict: { 'ai_response': str, 'session_id': str, 'router_decision': str, 'sleep': bool }
        """
        try:
            payload = {
                "user_input": question,
                "session_id": session_id
            }
            logger.info(f"Sending to RAG: {self.rag_endpoint}")
            logger.info(f"Payload: {payload}")

            response = requests.post(
                self.rag_endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"RAG response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"RAG JSON received: {data}")

                ai_response = data.get("ai_response", "")
                session_id = data.get("session_id", "")
                router_decision = data.get("router_decision", "")

                # If router_decision is goodbye, set sleep flag
                sleep = router_decision.lower() == "goodbye"

                return {
                    "ai_response": ai_response,
                    "session_id": session_id,
                    "router_decision": router_decision,
                    "sleep": sleep
                }
            else:
                logger.error(f"RAG failed with status {response.status_code}: {response.text}")
                return {
                    "ai_response": f"University system error (status {response.status_code}). Please try again.",
                    "session_id": session_id or "",
                    "router_decision": "error",
                    "sleep": False
                }

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to {self.rag_endpoint}: {e}")
            return {
                "ai_response": "Cannot connect to university information system. Please check your connection.",
                "session_id": session_id or "",
                "router_decision": "error",
                "sleep": False
            }

        except requests.exceptions.Timeout:
            logger.error(f"Timeout after {self.timeout}s")
            return {
                "ai_response": "University system is taking too long to respond. Please try again.",
                "session_id": session_id or "",
                "router_decision": "error",
                "sleep": False
            }

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "ai_response": f"Unexpected error: {str(e)}",
                "session_id": session_id or "",
                "router_decision": "error",
                "sleep": False
            }

    def health_check(self) -> bool:
        """Check if RAG endpoint is responding."""
        try:
            logger.info(f"Health check: {self.rag_endpoint}")
            test_payload = {"user_input": "test"}
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