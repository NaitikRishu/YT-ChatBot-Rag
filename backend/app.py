from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, validator
import re
import logging
from typing import Optional, List
from datetime import datetime

from backend.index_manager import build_index_for_video, load_existing_index
from backend.rag import get_rag_chain_with_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube RAG Chatbot API")

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# State management
CURRENT_RETRIEVER = None
CURRENT_VIDEO_ID = None
LAST_LOAD_TIME = None
CONVERSATION_HISTORY = []  


class LoadVideoRequest(BaseModel):
    video_url: HttpUrl
    
    @validator('video_url')
    def validate_youtube_url(cls, v):
        url_str = str(v)
        if 'youtube.com' not in url_str and 'youtu.be' not in url_str:
            raise ValueError('Must be a valid YouTube URL')
        return v


class Message(BaseModel):
    role: str 
    content: str
    timestamp: Optional[str] = None


class AskRequest(BaseModel):
    question: str
    conversation_history: Optional[List[Message]] = []
    
    @validator('question')
    def validate_question(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Question cannot be empty')
        if len(v) > 500:
            raise ValueError('Question too long (max 500 characters)')
        return v.strip()


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|/)([a-zA-Z0-9_-]{11})(?:\?|&|$|/)',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'embed/([a-zA-Z0-9_-]{11})',
        r'v/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("Could not extract video ID from URL")


@app.on_event("startup")
async def startup_event():
    """Try to load existing index on startup"""
    global CURRENT_RETRIEVER
    logger.info("Starting up application...")
    
    existing_retriever = load_existing_index()
    if existing_retriever:
        CURRENT_RETRIEVER = existing_retriever
        logger.info("Loaded existing index from disk")


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "YouTube RAG Chatbot API",
        "video_loaded": CURRENT_VIDEO_ID is not None,
        "current_video": CURRENT_VIDEO_ID,
        "last_load_time": LAST_LOAD_TIME.isoformat() if LAST_LOAD_TIME else None,
        "conversation_length": len(CONVERSATION_HISTORY)
    }


@app.post("/load_video")
async def load_video(req: LoadVideoRequest):
    """
    Load and index a YouTube video's transcript.
    Clears conversation history when loading a new video.
    """
    global CURRENT_RETRIEVER, CURRENT_VIDEO_ID, LAST_LOAD_TIME, CONVERSATION_HISTORY
    
    try:
        video_id = extract_video_id(str(req.video_url))
        logger.info(f"Loading video: {video_id}")
        
        # Check if same video is already loaded
        if CURRENT_VIDEO_ID == video_id and CURRENT_RETRIEVER is not None:
            logger.info(f"Video {video_id} already loaded, clearing chat history")
            # Clear conversation history but keep the video loaded
            CONVERSATION_HISTORY = []
            return {
                "message": "Video already loaded, chat history cleared",
                "video_id": video_id,
                "cached": True
            }
        
        # Build index
        logger.info("Building index - this may take 30-60 seconds...")
        CURRENT_RETRIEVER = build_index_for_video(video_id)
        CURRENT_VIDEO_ID = video_id
        LAST_LOAD_TIME = datetime.utcnow()
        
        # Clear conversation history for new video
        CONVERSATION_HISTORY = []
        
        logger.info(f"Successfully loaded video {video_id}")
        return {
            "message": "Video indexed successfully",
            "video_id": video_id,
            "cached": False
        }
        
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        error_msg = str(ve)
        
        # Provide helpful message for rate limiting
        if "rate limiting" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "YouTube Rate Limit",
                    "message": "YouTube is temporarily blocking requests from your network.",
                    "solutions": [
                        "Wait 1-2 hours and try again",
                        "Switch to a different network (mobile hotspot)",
                        "Use a VPN",
                        "Try a different video"
                    ],
                    "technical": error_msg
                }
            )
        
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Error loading video: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load video: {str(e)}"
        )


@app.post("/ask")
async def ask(req: AskRequest):
    """
    Ask a question about the loaded video.
    Supports conversation history for contextual responses.
    """
    global CURRENT_RETRIEVER, CONVERSATION_HISTORY
    
    if CURRENT_RETRIEVER is None:
        raise HTTPException(
            status_code=400,
            detail="No video loaded. Please load a video first using /load_video"
        )
    
    try:
        logger.info(f"Processing question: {req.question[:50]}...")
        
        # Use client-provided history if available, otherwise use server history
        history = req.conversation_history if req.conversation_history else CONVERSATION_HISTORY
        
        # Get RAG chain with history support
        rag_chain = get_rag_chain_with_history(CURRENT_RETRIEVER)
        
        # Format conversation history for context
        history_context = ""
        if history:
            history_context = "\n\nPrevious conversation:\n"
            for msg in history[-3:]:  # Last 3 messages for context
                role = "User" if msg.role == "user" else "Assistant"
                history_context += f"{role}: {msg.content}\n"
        
        # Invoke RAG chain with history context
        full_question = req.question
        if history_context:
            full_question = f"{history_context}\nCurrent question: {req.question}"
        
        answer = rag_chain.invoke(full_question)
        
        # Validate answer
        if not answer or len(answer.strip()) == 0:
            answer = "I couldn't generate a meaningful answer. Please rephrase your question."
        
        # Store in server-side history
        CONVERSATION_HISTORY.append(Message(
            role="user",
            content=req.question,
            timestamp=datetime.utcnow().isoformat()
        ))
        CONVERSATION_HISTORY.append(Message(
            role="assistant",
            content=answer,
            timestamp=datetime.utcnow().isoformat()
        ))
        
        # Keep only last 20 messages
        if len(CONVERSATION_HISTORY) > 20:
            CONVERSATION_HISTORY = CONVERSATION_HISTORY[-20:]
        
        logger.info(f"Generated answer (length: {len(answer)})")
        
        return {
            "answer": answer,
            "video_id": CURRENT_VIDEO_ID,
            "question": req.question,
            "conversation_length": len(CONVERSATION_HISTORY)
        }
        
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}"
        )


@app.get("/conversation")
async def get_conversation():
    """Get current conversation history"""
    return {
        "video_id": CURRENT_VIDEO_ID,
        "history": CONVERSATION_HISTORY,
        "length": len(CONVERSATION_HISTORY)
    }


@app.post("/conversation/clear")
async def clear_conversation():
    """Clear conversation history"""
    global CONVERSATION_HISTORY
    CONVERSATION_HISTORY = []
    return {"message": "Conversation history cleared"}


@app.get("/status")
async def status():
    """Get current system status"""
    return {
        "video_loaded": CURRENT_RETRIEVER is not None,
        "current_video_id": CURRENT_VIDEO_ID,
        "last_load_time": LAST_LOAD_TIME.isoformat() if LAST_LOAD_TIME else None,
        "ready_for_questions": CURRENT_RETRIEVER is not None,
        "conversation_length": len(CONVERSATION_HISTORY)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)