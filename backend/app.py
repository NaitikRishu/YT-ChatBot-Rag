from fastapi import FastAPI
from pydantic import BaseModel
import re

app = FastAPI()

class VideoRequest(BaseModel):
    video_url: str


def extract_video_id(url: str) -> str:
    """
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    """
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


from backend.index_manager import build_index_for_video

from backend.schemas import LoadVideoRequest


@app.post("/load_video")
def load_video(request: LoadVideoRequest):
    video_url = str(request.video_url) 
    video_id = extract_video_id(video_url)  # whatever logic you use

    return {
        "message": "Video accepted",
        "video_id": video_id
    }

