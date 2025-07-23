from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models.userstate import State
from models.chatmodel import ChatModel
from session_store import create_session, get_session, update_session, delete_session, get_all_sessions
from utils.executor import execute_node
from routes.nvidiaa2f import a2f_router
from utils.rag_client import rag_client

# Create FastAPI app
app = FastAPI(
    title="University Assistant API",
    description="3D Conversational University Assistant with RAG integration",
    version="1.0.0"
)

# Include A2F router for 3D face animation
app.include_router(a2f_router, tags=["a2f"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NO LLM NEEDED - Using RAG only


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "University Assistant API",
        "version": "1.0.0",
        "rag_endpoint": rag_client.rag_endpoint,
        "endpoints": {
            "session_init": "/session/",
            "chat": "/chat/",
            "sessions": "/get_all_sessions/",
            "health": "/health/",
            "a2f": "/a2f/"
        }
    }


@app.get("/health/")
async def health_check():
    """Health check endpoint."""
    rag_healthy = rag_client.health_check()
    return {
        "status": "healthy",
        "rag_system": "connected" if rag_healthy else "disconnected",
        "a2f": "available"
    }


@app.get("/session/")
async def init_session():
    """Initialize a new conversation session."""
    try:
        # Create initial state for university assistant
        state = State(
            name=None,
            history=[],
            retry_count=0,
            current_node="collect_name",
            next_question=None,
            session_id=None,
            last_query=None,
            conversation_ended=False
        )
        
        # Execute the collect_name node to get initial greeting (NO LLM)
        state = execute_node("collect_name", None, state)  # Pass None for llm
        
        # Create session and store state
        session_id = create_session(state)
        state["session_id"] = str(session_id)
        update_session(session_id, state)
        
        return {
            "session_id": str(session_id),
            "state": state,
            "message": "University assistant session initialized successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")


@app.post("/chat/")
async def chat(chat_model: ChatModel):
    """Handle chat interaction with the university assistant."""
    try:
        session_id = chat_model["session_id"]
        user_input = chat_model["user_input"]
        
        # Get session
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        state = session
        
        # Get current node or default to university_chat
        current_node = state.get("current_node", "university_chat")
        
        # If conversation ended, don't process further
        if state.get("conversation_ended", False):
            return {
                "session_id": session_id,
                "state": state,
                "message": "Conversation has ended. Please start a new session."
            }
        
        # Execute current node with user input (NO LLM)
        state = execute_node(current_node, None, state, user_input)  # Pass None for llm
        
        # Get next node and execute if different
        next_node = state.get("current_node")
        if next_node and next_node != current_node:
            state = execute_node(next_node, None, state)  # Pass None for llm
        
        # Update session
        update_session(session_id, state)
        
        return {
            "session_id": session_id,
            "state": state,
            "message": "Response generated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    """End a conversation session."""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Clear RAG context
        rag_client.clear_session_context(session_id)
        
        # Delete session
        delete_session(session_id)
        
        return {
            "message": f"Session {session_id} ended successfully",
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@app.get("/get_all_sessions/")
async def get_all_sessions_endpoint():
    """Get all active sessions."""
    try:
        sessions = get_all_sessions()
        return {
            "total_sessions": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")


@app.post("/rag/test/")
async def test_rag_endpoint(query_data: dict):
    """Test RAG endpoint connectivity."""
    try:
        query = query_data.get("query", "What are the university's admission requirements?")
        response = rag_client.query_university_info(query)
        
        return {
            "query": query,
            "response": response,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "query": query_data.get("query", ""),
            "response": f"RAG test failed: {str(e)}",
            "status": "error"
        }


@app.get("/sessions/stats/")
async def session_stats():
    """Get session statistics."""
    try:
        sessions = get_all_sessions()
        total_sessions = len(sessions)
        
        node_counts = {}
        conversation_ended_count = 0
        
        for session_id, session_data in sessions.items():
            current_node = session_data.get("current_node", "unknown")
            node_counts[current_node] = node_counts.get(current_node, 0) + 1
            
            if session_data.get("conversation_ended", False):
                conversation_ended_count += 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": total_sessions - conversation_ended_count,
            "ended_sessions": conversation_ended_count,
            "sessions_by_node": node_counts,
            "rag_system_healthy": rag_client.health_check()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session stats: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    print("🎓 University Assistant API starting up...")
    print(f"RAG endpoint: {rag_client.rag_endpoint}")
    print("🚀 University Assistant API ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("🎓 University Assistant API shutting down...")
    for session_id in get_all_sessions().keys():
        rag_client.clear_session_context(session_id)
    print("👋 University Assistant API stopped!")