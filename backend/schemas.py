from pydantic import BaseModel, HttpUrl

class LoadVideoRequest(BaseModel):
    video_url: HttpUrl
