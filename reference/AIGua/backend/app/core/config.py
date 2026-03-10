from pydantic import BaseModel
from typing import List, Optional
import yaml
import os
from pathlib import Path

class MediaLibrary(BaseModel):
    path: str
    type: str  # 'movie' 或 'tv'

class Settings(BaseModel):
    # API Keys
    grok_api_key: str = ""
    tmdb_api_key: str = ""
    
    # Media Libraries
    media_libraries: List[MediaLibrary] = []
    
    # API Settings
    grok_batch_size: int = 20
    grok_rate_limit: int = 1  # 每秒最大请求次数
    tmdb_rate_limit: int = 50  # 每秒最大请求次数
    proxy_url: str = ""
    
    # Media Extensions
    media_extension: str = ".mp4;.iso;.mkv;.mov"  # 支持的媒体文件扩展名，分号分隔
    subtitle_extension: str = ".srt;.ass;.ssa"  # 支持的字幕文件扩展名，分号分隔
    
    class Config:
        env_file = ".env"

class ConfigManager:
    def __init__(self):
        # 使用相对于项目根目录的路径
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.config_file = self.config_dir / "config.yaml"
        self._settings = None
        self.load_config()

    @property
    def settings(self):
        """获取当前配置"""
        return self._settings

    def load_config(self):
        """Load configuration from YAML file."""
        print(f"正在加载配置文件: {self.config_file}")
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
                print(f"从文件加载的配置数据: {config_data}")
                if config_data:
                    # 确保 media_libraries 是 MediaLibrary 对象的列表
                    if "media_libraries" in config_data:
                        # 处理单个媒体库的情况
                        if isinstance(config_data["media_libraries"], dict):
                            config_data["media_libraries"] = [config_data["media_libraries"]]
                        # 确保每个媒体库都是 MediaLibrary 对象
                        config_data["media_libraries"] = [
                            MediaLibrary(**lib) if isinstance(lib, dict) else lib
                            for lib in config_data["media_libraries"]
                            if lib and isinstance(lib, (dict, MediaLibrary))
                        ]
                        print(f"处理后的媒体库配置: {config_data['media_libraries']}")
                    # 保持原始大小写，不进行转换
                    self._settings = Settings(**config_data)
                    print(f"最终加载的配置: {self._settings.dict()}")
                else:
                    print("配置文件为空，使用默认配置")
                    self._settings = Settings()
        else:
            print("配置文件不存在，使用默认配置")
            self._settings = Settings()

    def save_config(self, settings: Settings):
        """Save configuration to YAML file."""
        print(f"正在保存配置到文件: {self.config_file}")
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 将设置转换为字典
        config_data = settings.dict()
        print(f"要保存的配置数据: {config_data}")
        
        # 保存到文件
        with open(self.config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, sort_keys=False)
        
        # 更新内存中的设置
        self._settings = settings
        print("配置保存成功")

    def refresh_settings(self):
        """强制刷新配置"""
        print("强制刷新配置...")
        self.load_config()
        return self._settings

# Create a global config manager instance
config_manager = ConfigManager()
settings = config_manager.settings 


def get_config_manager() -> ConfigManager:
    """FastAPI dependency helper returning the singleton config manager."""
    return config_manager