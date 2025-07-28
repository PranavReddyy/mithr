from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uuid
import logging
import os
from dotenv import load_dotenv
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

from models.chatmodel import ChatModel
from utils.rag_client import rag_client
from routes.nvidiaa2f import a2f_router

# Create FastAPI app
app = FastAPI(
    title="University Assistant API",
    description="Simple RAG-based University Assistant with TTS/STT/A2F",
    version="1.0.0"
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Mounted static directory: {static_dir}")

# Include A2F router
app.include_router(a2f_router, prefix="/a2f", tags=["a2f"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://v2881qgw-3000.use.devtunnels.ms",
        "https://v2881qgw-8002.use.devtunnels.ms",
        "*"  # Allow all origins for development (remove in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/static/mithr.ppn")
async def get_mithr_ppn():
    """Serve the Porcupine wake word file"""
    file_path = os.path.join(os.path.dirname(__file__), "static", "mithr.ppn")
    logger.info(f"Requesting mithr.ppn from: {file_path}")
    if os.path.exists(file_path):
        return FileResponse(
            file_path, 
            media_type="application/octet-stream",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600"
            }
        )
    logger.error(f"Wake word file not found at: {file_path}")
    raise HTTPException(status_code=404, detail="Wake word file not found")

@app.get("/static/porcupine_params.pv")
async def get_porcupine_params():
    """Serve the Porcupine model parameters file"""
    file_path = os.path.join(os.path.dirname(__file__), "static", "porcupine_params.pv")
    logger.info(f"Requesting porcupine_params.pv from: {file_path}")
    if os.path.exists(file_path):
        return FileResponse(
            file_path, 
            media_type="application/octet-stream",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600"
            }
        )
    logger.error(f"Model parameters file not found at: {file_path}")
    raise HTTPException(status_code=404, detail="Model parameters file not found")

# Simple in-memory session store
sessions = {}

@app.post("/session/init")
async def create_session():
    """Create a new session and return its ID and the initial state."""
    session_id = str(uuid.uuid4())
    
    # Keep it simple: Use a hardcoded initial state to avoid RAG client errors on init.
    # The actual RAG logic will be engaged in the /chat endpoint.
    initial_state = {
        "next_question": "Welcome to the University Assistant! How can I help you today?",
        "conversation_history": [],
        "conversation_ended": False
    }
    
    sessions[session_id] = initial_state
    logger.info(f"New session created with simple init: {session_id}")
    return {"session_id": session_id, "state": initial_state}

@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {"message": "University Assistant API is running. See /docs for details."}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check called")
    rag_healthy = rag_client.health_check()
    
    # Check A2F status
    try:
        from routes.nvidiaa2f import client, whisper_model, A2F_AVAILABLE
        tts_available = client is not None
        stt_available = whisper_model is not None
    except:
        tts_available = False
        stt_available = False
        A2F_AVAILABLE = False
    
    health_status = {
        "status": "healthy",
        "rag_system": "connected" if rag_healthy else "disconnected",
        "rag_endpoint": rag_client.rag_endpoint,
        "tts_available": tts_available,
        "stt_available": stt_available,
        "a2f_available": A2F_AVAILABLE,
        "timestamp": "2024-01-01"
    }
    logger.info(f"Health status: {health_status}")
    return health_status

@app.post("/chat")
async def chat_endpoint(request: ChatModel):
    """Simple stateless chat endpoint. No session tracking."""
    logger.info(f"Stateless chat endpoint called with message: '{request.message}'")
    
    try:
        # Directly query the RAG client without session_id
        response_text = rag_client.query_university_info(request.message)
        logger.info(f"Got response from RAG: {response_text[:100] if response_text else 'None'}...")
        
        # Return a simple, direct response object.
        return {"response": response_text}
        
    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.get("/sessions")
async def get_sessions():
    """Get all sessions"""
    return {"sessions": list(sessions.keys()), "count": len(sessions)}

@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} cleared"}
    return {"message": "Session not found"}

@app.get("/rag/health")
async def rag_health():
    """RAG system health check"""
    healthy = rag_client.health_check()
    return {
        "rag_healthy": healthy,
        "endpoint": rag_client.rag_endpoint,
        "status": "connected" if healthy else "disconnected"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)