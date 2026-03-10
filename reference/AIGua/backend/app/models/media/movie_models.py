from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class MovieFile(BaseModel):
    """Represents a movie file with its associated files"""
    file_path: str
    file_name: str
    file_size: int
    modified_time: datetime
    selected: bool = True
    new_name: str = ""
    movie_info: Optional[Dict] = None  # TMDB movie info
    subtitles: List[str] = []  # Associated subtitle files

class Movie(BaseModel):
    """Represents a movie with its files"""
    tmdb_id: Optional[str] = None
    title: str
    original_title: Optional[str] = None
    year: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    directory_path: str
    files: List[MovieFile] = []
    selected: bool = True
    new_name: str = ""
    movie_info: Optional[Dict] = None  # TMDB movie info 