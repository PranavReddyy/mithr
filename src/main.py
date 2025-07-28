import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from utils.rag_client import rag_client

# Set up project name
os.environ["LANGCHAIN_PROJECT"] = "UNIVERSITY_ASSISTANT"

def process_user_input(user_input, session_id=None):
    """Simple function to process user input directly through RAG"""
    return rag_client.query_university_info(user_input, session_id)