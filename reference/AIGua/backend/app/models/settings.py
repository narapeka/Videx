from pydantic import BaseModel
from typing import List, Optional
from ..core.config import MediaLibrary

class Settings(BaseModel):
    """Settings model for the application."""
    grok_api_key: Optional[str] = None
    tmdb_api_key: Optional[str] = None
    media_libraries: List[MediaLibrary] = []
    grok_batch_size: Optional[int] = 20
    grok_rate_limit: Optional[int] = 1
    tmdb_rate_limit: Optional[int] = 50
    proxy_url: Optional[str] = None
    media_extension: Optional[str] = ".iso;.mkv;.mp4;.ts;.m2ts;.avi;.mov;.mpeg"
    subtitle_extension: Optional[str] = ".srt;.ass;.ssa" 