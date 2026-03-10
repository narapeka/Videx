from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models.media.tv_models import TVShow
from ..services.tv_show_service import TVShowService
from ..core.config import get_config_manager

router = APIRouter(prefix="/tv", tags=["tv"])

@router.get("/scan")
async def scan_tv_shows(
    full_scan: bool = False,
    config_manager = Depends(get_config_manager)
):
    """Scan TV show directories"""
    try:
        tv_service = TVShowService(config_manager)
        shows = []
        
        # Get TV show libraries
        tv_libraries = [
            lib for lib in config_manager.settings.media_libraries
            if lib.type == 'tv'
        ]
        
        for library in tv_libraries:
            show = await tv_service.scan_directory(library.path)
            shows.append(show)
        
        return {"shows": shows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/identify")
async def identify_tv_shows(
    shows: List[TVShow],
    config_manager = Depends(get_config_manager)
):
    """Identify TV shows and their episodes"""
    try:
        tv_service = TVShowService(config_manager)
        identified_shows = []
        
        for show in shows:
            identified_show = await tv_service.identify_episodes(show)
            identified_shows.append(identified_show)
        
        return {"shows": identified_shows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rename")
async def rename_tv_shows(
    shows: List[TVShow],
    config_manager = Depends(get_config_manager)
):
    """Rename TV shows and their episodes"""
    try:
        tv_service = TVShowService(config_manager)
        results = []
        
        for show in shows:
            result = await tv_service.rename_show(show)
            results.extend(result)
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 