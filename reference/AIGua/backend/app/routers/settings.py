from fastapi import APIRouter, HTTPException
from ..models.settings import Settings
from ..core.config import config_manager

router = APIRouter()

@router.get("/")
async def get_settings():
    """Get current settings."""
    try:
        print("正在获取设置...")
        settings = config_manager.settings
        print(f"当前设置: {settings.dict()}")
        return settings
    except Exception as e:
        print(f"获取设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def save_settings(settings: Settings):
    """Save settings to config file."""
    try:
        print(f"收到保存设置请求: {settings.dict()}")
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
        print("设置保存成功")
        return settings
    except Exception as e:
        print(f"保存设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 