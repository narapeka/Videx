"""File scanning router for listing directories and scanning media files."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import os
from pydantic import BaseModel
from ..core.config import settings, config_manager
from ..utils.file_utils import safe_path_exists

router = APIRouter(tags=["file_scanner"])

class DirectoryInfo(BaseModel):
    name: str
    path: str

class DirectoryList(BaseModel):
    directories: List[DirectoryInfo]

@router.get("/directories", response_model=DirectoryList)
async def list_directories(path: str = ""):
    """List directories at the specified path."""
    try:
        if not path:
            # 如果没有指定路径，返回系统根目录
            if os.name == 'nt':  # Windows
                drives = []
                for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        drives.append(DirectoryInfo(name=drive, path=drive))
                return DirectoryList(directories=drives)
            else:  # Unix-like
                return DirectoryList(directories=[DirectoryInfo(name="/", path="/")])
        
        # 确保路径存在且是目录
        if not os.path.exists(path) or not os.path.isdir(path):
            raise HTTPException(status_code=404, detail="Directory not found")
        
        # 获取目录内容
        items = os.listdir(path)
        directories = []
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                directories.append(DirectoryInfo(name=item, path=full_path))
        
        return DirectoryList(directories=sorted(directories, key=lambda x: x.name.lower()))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scan")
async def scan_files(full_scan: bool = False):
    """
    扫描所有配置的媒体库中的媒体文件。
    
    Args:
        full_scan: 是否进行全量扫描。如果为False，将只扫描不符合命名规范的目录。
    """
    try:
        # 强制刷新配置
        current_settings = config_manager.refresh_settings()
        print(f"刷新后的配置: {current_settings.dict()}")
        
        all_files = []
        print(f"开始扫描媒体库，当前配置的媒体库数量: {len(current_settings.media_libraries)}")
        print(f"扫描模式: {'全量扫描' if full_scan else '增量扫描'}")
        
        if not current_settings.media_libraries:
            print("警告: 没有配置媒体库")
            return {"files": []}
        
        # 获取媒体文件扩展名列表
        media_extensions = current_settings.media_extension.split(';')
        print(f"将识别以下媒体文件扩展名: {media_extensions}")
        
        # 判断目录是否符合命名规范的函数
        def is_well_named_directory(directory_name):
            """
            判断目录名是否符合命名规范
            检查目录名是否满足格式: ??? (年份) {tmdb-???}
            """
            import re
            # 检查是否同时包含年份格式 (YYYY) 和 tmdb ID {tmdb-数字}
            year_pattern = re.compile(r'[(|\[]?(19|20)\d{2}[)|\]]?')
            tmdb_pattern = re.compile(r'\{tmdb-\d+\}')
            
            has_year = bool(year_pattern.search(directory_name))
            has_tmdb_id = bool(tmdb_pattern.search(directory_name))
            
            # 必须同时包含年份和tmdb ID才算符合规范
            return has_year and has_tmdb_id
        
        for library in current_settings.media_libraries:
            if not library:
                print("跳过无效的媒体库配置")
                continue
                
            # 获取媒体库路径
            library_path = library.path if hasattr(library, 'path') else library.get('path')
            if not library_path:
                print(f"媒体库配置缺少 path 属性: {library}")
                continue
                
            print(f"正在处理媒体库: {library_path}")
            
            if not os.path.exists(library_path):
                print(f"媒体库路径不存在: {library_path}")
                continue
                
            if not os.path.isdir(library_path):
                print(f"媒体库路径不是目录: {library_path}")
                continue
                
            print(f"开始扫描媒体库: {library_path}")
            try:
                # 1. 首先扫描媒体库根目录下的文件（无论是全量还是增量扫描）
                for file in os.listdir(library_path):
                    file_path = os.path.join(library_path, file)
                    # 只处理文件（不是目录）
                    if os.path.isfile(file_path):
                        # 检查文件是否具有配置的任意一种扩展名
                        if any(file.lower().endswith(ext.lower()) for ext in media_extensions):
                            print(f"找到根目录媒体文件: {file_path}")
                            all_files.append(file_path)
                
                # 2. 再扫描子目录（根据扫描模式决定是否跳过规范命名的目录）
                root_subdirs = [d for d in os.listdir(library_path) 
                              if os.path.isdir(os.path.join(library_path, d))]
                
                for subdir in root_subdirs:
                    subdir_path = os.path.join(library_path, subdir)
                    
                    # 如果是增量扫描且子目录名称符合规范，则跳过该目录
                    if not full_scan and is_well_named_directory(subdir):
                        print(f"增量扫描模式: 跳过已符合命名规范的目录: {subdir_path}")
                        continue
                    
                    # 扫描子目录下的所有文件
                    for root, _, files in os.walk(subdir_path):
                        for file in files:
                            # 检查文件是否具有配置的任意一种扩展名
                            if any(file.lower().endswith(ext.lower()) for ext in media_extensions):
                                full_path = os.path.join(root, file)
                                print(f"找到媒体文件: {full_path}")
                                all_files.append(full_path)
            except Exception as e:
                print(f"扫描目录 {library_path} 时出错: {str(e)}")
                continue
        
        print(f"扫描完成，找到 {len(all_files)} 个媒体文件")
        return {"files": all_files}
    except Exception as e:
        print(f"扫描文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 