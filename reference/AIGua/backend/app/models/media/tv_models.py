from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class TVEpisode(BaseModel):
    """Represents a single episode file"""
    file_path: str
    file_name: str
    file_size: int
    modified_time: datetime
    selected: bool = True
    new_name: str = ""
    episode_info: Optional[Dict] = None  # TMDB episode info
    subtitles: List[str] = []  # Associated subtitle files

class TVSeason(BaseModel):
    """Represents a season directory containing episodes"""
    season_number: int
    directory_path: str
    episodes: List[TVEpisode] = []
    selected: bool = True
    new_name: str = ""
    season_info: Optional[Dict] = None  # TMDB season info

class TVShow(BaseModel):
    """Represents a TV show with multiple seasons"""
    tmdb_id: Optional[str] = None
    title: str
    original_title: Optional[str] = None
    year: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    root_path: str
    seasons: Dict[int, TVSeason] = {}  # season_number -> TVSeason
    selected: bool = True
    new_name: str = ""
    show_info: Optional[Dict] = None  # TMDB show info 