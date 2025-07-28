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
        response = requests.get(f"{BASE_URL}/health", headers=HEADERS)
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

def test_rag_health():
    """Test RAG health endpoint."""
    print("🤖 Testing RAG health...")
    try:
        response = requests.get(f"{BASE_URL}/rag/health", headers=HEADERS)
        if response.status_code == 200:
            rag_data = response.json()
            print(f"✅ RAG health check passed: {rag_data}")
            return True
        else:
            print(f"❌ RAG health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ RAG health check error: {e}")
        return False

def test_a2f_status():
    """Test A2F system status."""
    print("🎬 Testing A2F status...")
    try:
        response = requests.get(f"{BASE_URL}/a2f/status", headers=HEADERS)
        if response.status_code == 200:
            a2f_data = response.json()
            print(f"✅ A2F status check passed: {a2f_data}")
            return True
        else:
            print(f"❌ A2F status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ A2F status check error: {e}")
        return False

def test_chat(message: str, session_id: str = None) -> dict:
    """Test chat endpoint."""
    print(f"💬 Testing chat with: '{message}'")
    try:
        payload = {
            "message": message,
            "session_id": session_id or "test_session"
        }
        response = requests.post(f"{BASE_URL}/chat", json=payload, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chat response: {data['response'][:100]}...")
            return data
        else:
            print(f"❌ Chat failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return None

def interactive_chat():
    """Run interactive chat with the university assistant."""
    print("🎓 University Assistant Simple Test Client")
    print("=" * 50)
    
    # Run health checks first
    if not test_health_check():
        print("⚠️  Main health check failed, but continuing...")
    
    if not test_rag_health():
        print("⚠️  RAG health check failed, but continuing...")
    
    if not test_a2f_status():
        print("⚠️  A2F status check failed, but continuing...")
    
    session_id = f"test_session_{hash(str(id))}"
    
    print(f"\n🎯 Session ID: {session_id}")
    print("\nCommands:")
    print("  - Type your questions normally")
    print("  - 'quit' or 'exit' to end conversation")
    print("  - 'health' to run health checks")
    print("  - 'sessions' to see session info")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
                
            # Handle special commands
            if user_input.lower() in ['quit', 'exit']:
                print("👋 Ending conversation...")
                break
                
            elif user_input.lower() == 'health':
                test_health_check()
                test_rag_health()
                test_a2f_status()
                continue
                
            elif user_input.lower() == 'sessions':
                try:
                    response = requests.get(f"{BASE_URL}/sessions", headers=HEADERS)
                    if response.status_code == 200:
                        sessions_data = response.json()
                        print(f"📊 Sessions: {sessions_data}")
                    else:
                        print(f"❌ Failed to get sessions: {response.status_code}")
                except Exception as e:
                    print(f"❌ Sessions error: {e}")
                continue
            
            # Send message to assistant
            result = test_chat(user_input, session_id)
            if result:
                print(f"🎓 University Assistant: {result['response']}")
            else:
                print("❌ Failed to get response")
                
        except KeyboardInterrupt:
            print("\n\n⌨️  Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break
    
    print("👋 Goodbye!")

def run_automated_test():
    """Run automated test sequence."""
    print("🧪 Running Automated Test Sequence")
    print("=" * 50)
    
    # Test all health endpoints
    test_health_check()
    test_rag_health()
    test_a2f_status()
    
    # Test chat functionality
    test_queries = [
        "Hello, what can you help me with?",
        "What are the admission requirements?",
        "Tell me about the computer science program",
        "What are the tuition fees?",
        "Thank you, goodbye"
    ]
    
    session_id = "automated_test_session"
    
    for query in test_queries:
        print(f"\n🧪 Testing query: {query}")
        result = test_chat(query, session_id)
        if not result:
            print("❌ Test failed, stopping")
            break
    
    # Test sessions endpoint
    try:
        response = requests.get(f"{BASE_URL}/sessions", headers=HEADERS)
        if response.status_code == 200:
            sessions_data = response.json()
            print(f"\n📊 Final Sessions: {sessions_data}")
    except Exception as e:
        print(f"❌ Sessions check error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        run_automated_test()
    else:
        interactive_chat()