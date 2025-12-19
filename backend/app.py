from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import re

from backend.index_manager import build_index_for_video
from backend.rag import get_rag_chain

app = FastAPI()


CURRENT_RETRIEVER = None


class LoadVideoRequest(BaseModel):
    video_url: HttpUrl

class AskRequest(BaseModel):
    question: str


def extract_video_id(url: str) -> str:
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError("Invalid YouTube URL")


@app.post("/load_video")
def load_video(req: LoadVideoRequest):
    global CURRENT_RETRIEVER
    
    try:
        video_id = extract_video_id(str(req.video_url))
        CURRENT_RETRIEVER = build_index_for_video(video_id)
        return {"message": "Video indexed successfully", "video_id": video_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load video: {str(e)}")

@app.post("/ask")
def ask(req: AskRequest):
    global CURRENT_RETRIEVER
    
    if CURRENT_RETRIEVER is None:
        raise HTTPException(
            status_code=400, 
            detail="No video loaded. Please load a video first using /load_video"
        )
    
    try:
        
        rag_chain = get_rag_chain(CURRENT_RETRIEVER)
        answer = rag_chain.invoke(req.question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")