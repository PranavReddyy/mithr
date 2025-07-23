import requests
import json
import sys
from typing import Optional

# Configuration
BASE_URL = "http://127.0.0.1:8000"
HEADERS = {'accept': 'application/json', 'Content-Type': 'application/json'}


def test_health_check():
    """Test the health endpoint."""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health/", headers=HEADERS)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_rag_endpoint():
    """Test RAG endpoint connectivity."""
    print("🤖 Testing RAG endpoint...")
    try:
        test_query = {"query": "What are the university's admission requirements?"}
        response = requests.post(f"{BASE_URL}/rag/test/", json=test_query, headers=HEADERS)
        if response.status_code == 200:
            rag_data = response.json()
            print(f"✅ RAG test passed: {rag_data['status']}")
            print(f"📝 RAG response: {rag_data['response'][:100]}...")
            return True
        else:
            print(f"❌ RAG test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ RAG test error: {e}")
        return False


def initialize_session() -> Optional[str]:
    """Initialize a new conversation session."""
    print("🚀 Initializing university assistant session...")
    try:
        response = requests.get(f"{BASE_URL}/session/", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            initial_question = data['state']['next_question']
            print(f"✅ Session initialized: {session_id}")
            print(f"🎓 University Assistant: {initial_question}")
            return session_id
        else:
            print(f"❌ Session initialization failed: {response.status_code}")
            print(f"Error: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Session initialization error: {e}")
        return None


def send_message(session_id: str, user_input: str) -> bool:
    """Send a message to the university assistant."""
    try:
        payload = {
            "session_id": session_id,
            "user_input": user_input
        }
        response = requests.post(f"{BASE_URL}/chat/", json=payload, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            bot_response = data['state']['next_question']
            current_node = data['state'].get('current_node', 'unknown')
            conversation_ended = data['state'].get('conversation_ended', False)
            
            print(f"🎓 University Assistant: {bot_response}")
            print(f"   [Node: {current_node}]")
            
            return not conversation_ended
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            print(f"❌ Error: {error_detail}")
            return False
            
    except Exception as e:
        print(f"❌ Message sending error: {e}")
        return False


def end_session(session_id: str):
    """End the conversation session."""
    try:
        response = requests.delete(f"{BASE_URL}/session/{session_id}", headers=HEADERS)
        if response.status_code == 200:
            print(f"✅ Session {session_id} ended successfully")
        else:
            print(f"❌ Failed to end session: {response.status_code}")
    except Exception as e:
        print(f"❌ Session ending error: {e}")


def get_session_stats():
    """Get session statistics."""
    try:
        response = requests.get(f"{BASE_URL}/sessions/stats/", headers=HEADERS)
        if response.status_code == 200:
            stats = response.json()
            print(f"📊 Session Statistics:")
            print(f"   Total sessions: {stats['total_sessions']}")
            print(f"   Active sessions: {stats['active_sessions']}")
            print(f"   Sessions by node: {stats['sessions_by_node']}")
            print(f"   RAG system healthy: {stats['rag_system_healthy']}")
        else:
            print(f"❌ Failed to get stats: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats error: {e}")


def interactive_chat():
    """Run interactive chat with the university assistant."""
    print("🎓 University Assistant Test Client")
    print("=" * 50)
    
    # Run health checks first
    if not test_health_check():
        print("⚠️  Health check failed, but continuing...")
    
    if not test_rag_endpoint():
        print("⚠️  RAG endpoint test failed, but continuing...")
    
    # Initialize session
    session_id = initialize_session()
    if not session_id:
        print("❌ Cannot start conversation without session")
        return
    
    print("\nCommands:")
    print("  - Type your questions normally")
    print("  - 'quit' or 'exit' to end conversation")
    print("  - 'stats' to see session statistics")
    print("  - 'help' to see this message again")
    print("-" * 50)
    
    conversation_active = True
    
    while conversation_active:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
                
            # Handle special commands
            if user_input.lower() in ['quit', 'exit']:
                print("👋 Ending conversation...")
                end_session(session_id)
                break
                
            elif user_input.lower() == 'stats':
                get_session_stats()
                continue
                
            elif user_input.lower() == 'help':
                print("\nCommands:")
                print("  - Type your questions normally")
                print("  - 'quit' or 'exit' to end conversation")
                print("  - 'stats' to see session statistics")
                print("  - 'help' to see this message again")
                continue
            
            # Send message to assistant
            conversation_active = send_message(session_id, user_input)
            
            if not conversation_active:
                print("🎓 Conversation ended by assistant")
                end_session(session_id)
                
        except KeyboardInterrupt:
            print("\n\n⌨️  Interrupted by user")
            end_session(session_id)
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break
    
    print("👋 Goodbye!")


def run_automated_test():
    """Run automated test sequence."""
    print("🧪 Running Automated Test Sequence")
    print("=" * 50)
    
    # Test health
    test_health_check()
    test_rag_endpoint()
    
    # Test conversation flow
    session_id = initialize_session()
    if not session_id:
        return
    
    # Test name collection
    print("\n🧪 Testing name collection...")
    send_message(session_id, "John Doe")
    
    # Test university queries
    test_queries = [
        "What are the admission requirements?",
        "Tell me about the computer science program",
        "What are the tuition fees?",
        "goodbye"
    ]
    
    for query in test_queries:
        print(f"\n🧪 Testing query: {query}")
        if not send_message(session_id, query):
            break
    
    # Get final stats
    print("\n📊 Final Statistics:")
    get_session_stats()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        run_automated_test()
    else:
        interactive_chat()