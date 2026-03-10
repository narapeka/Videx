from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models.media.movie_models import Movie
from ..services.movie_service import MovieService
from ..core.config import get_config_manager

router = APIRouter(prefix="/movies", tags=["movies"])

@router.get("/scan")
async def scan_movies(
    full_scan: bool = False,
    config_manager = Depends(get_config_manager)
):
    """Scan movie directories"""
    try:
        movie_service = MovieService(config_manager)
        movies = []
        
        # Get movie libraries
        movie_libraries = [
            lib for lib in config_manager.settings.media_libraries
            if lib.type == 'movie'
        ]
        
        for library in movie_libraries:
            library_movies = await movie_service.scan_directory(library.path)
            movies.extend(library_movies)
        
        return {"movies": movies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/identify")
async def identify_movies(
    movies: List[Movie],
    config_manager = Depends(get_config_manager)
):
    """Identify movies"""
    try:
        movie_service = MovieService(config_manager)
        identified_movies = await movie_service.identify_movies(movies)
        return {"movies": identified_movies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rename")
async def rename_movies(
    movies: List[Movie],
    config_manager = Depends(get_config_manager)
):
    """Rename movies"""
    try:
        movie_service = MovieService(config_manager)
        results = await movie_service.rename_movies(movies)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 