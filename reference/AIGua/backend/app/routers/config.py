from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from ..core.config import config_manager, settings, MediaLibrary
from ..models.settings import Settings

router = APIRouter()

class ConfigUpdate(BaseModel):
    grok_api_key: str = None
    tmdb_api_key: str = None
    media_libraries: List[MediaLibrary] = None
    grok_batch_size: int = None
    grok_rate_limit: int = None
    tmdb_rate_limit: int = None
    proxy_url: str = None

@router.get("/")
async def get_config():
    """Get current configuration."""
    try:
        print("正在获取配置...")
        settings = config_manager.settings
        print(f"当前配置: {settings.dict()}")
        return settings
    except Exception as e:
        print(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def update_config(settings: Settings):
    """Update configuration."""
    try:
        print(f"收到更新配置请求: {settings.dict()}")
        # 验证媒体库配置
        if not settings.media_libraries:
            print("警告: 没有配置媒体库")
            # 允许空媒体库配置
            pass
        else:
            for library in settings.media_libraries:
                if not library.path or not library.type:
                    raise HTTPException(status_code=400, detail="媒体库配置不完整，请确保每个媒体库都包含路径和类型")
        
        # 保存配置
        config_manager.save_config(settings)
        print("配置保存成功")
        return settings
    except Exception as e:
        print(f"更新配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-connection")
async def test_connection():
    """Test API connections."""
    # TODO: Implement connection testing for Grok and TMDB APIs
    return {"message": "Connection test completed"} 