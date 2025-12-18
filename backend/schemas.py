# backend/schemas.py
from pydantic import BaseModel, HttpUrl

class LoadVideoRequest(BaseModel):
    video_url: HttpUrl

class AskRequest(BaseModel):
    question: str
