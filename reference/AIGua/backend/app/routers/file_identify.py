"""File identification router to identify media files using TMDB."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Optional
import os
from pydantic import BaseModel
from ..core.config import config_manager
from ..services.api import MediaInfoService
import asyncio
import traceback
import json
import logging
from datetime import datetime
import shutil
import re

router = APIRouter(tags=["file_identify"])

# Create media service instance
media_service = MediaInfoService()

class TMDBInfo(BaseModel):
    """TMDB信息模型，正确定义各字段类型"""
    id: Optional[str] = None
    title: Optional[str] = None
    original_title: Optional[str] = None
    year: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    vote_average: Optional[float] = None
    popularity: Optional[float] = None
    
    class Config:
        """允许额外字段和类型转换"""
        extra = "allow"
        smart_union = True

class FileInfo(BaseModel):
    original_path: str
    selected: Optional[bool] = False
    tmdb: Optional[dict] = None
    error: Optional[str] = None
    new_name: Optional[str] = None
    new_sub_folder: Optional[str] = None

class FileList(BaseModel):
    files: List[FileInfo]

class FileDetailsRequest(BaseModel):
    file_path: str
    
class FileDetailsResponse(BaseModel):
    full_path: str
    creation_time: str
    modification_time: str
    size: int

class DeleteFileRequest(BaseModel):
    file_path: str
    
class DeleteFileResponse(BaseModel):
    success: bool
    message: str

@router.post("/identify")
async def identify_files(files: List[FileInfo]):
    """Identify files using Grok AI and TMDB API with parallel processing."""
    try:
        print(f"开始处理 {len(files)} 个文件")
        
        # 重新加载配置并创建新的MediaInfoService实例以应用最新的速率限制设置
        current_settings = config_manager.refresh_settings()
        print(f"使用刷新后的配置: grok_rate_limit={current_settings.grok_rate_limit}, tmdb_rate_limit={current_settings.tmdb_rate_limit}")
        
        # 创建新的服务实例，确保使用最新配置
        new_media_service = MediaInfoService()
        
        # 获取媒体库路径列表和类型
        media_libraries = {lib.path: lib.type for lib in current_settings.media_libraries if hasattr(lib, 'path') and lib.path}
        media_library_paths = list(media_libraries.keys())
        print(f"已配置的媒体库路径: {media_library_paths}")
        
        # 提取所有文件路径，并去除媒体库路径前缀
        original_paths = [file.original_path for file in files]
        simplified_paths = []
        path_mapping = {}  # 用于保存简化路径到原始路径的映射
        file_media_types = {}  # 用于保存文件到媒体库类型的映射 (movie/tv)
        
        for original_path in original_paths:
            # 查找此文件所属的媒体库
            matching_library = None
            for lib_path in media_library_paths:
                if original_path.startswith(lib_path):
                    matching_library = lib_path
                    break
            
            if matching_library:
                # 记录文件的媒体类型
                media_type = media_libraries.get(matching_library)
                print(f"文件 {original_path} 属于媒体库类型: {media_type}")
                
                # 从路径中去除媒体库前缀，保留相对路径部分
                relative_path = original_path[len(matching_library):].lstrip('\\/')
                simplified_path = os.path.basename(original_path)  # 默认使用文件名
                
                # 如果相对路径包含目录结构信息，保留它
                if os.path.dirname(relative_path):
                    simplified_path = relative_path
                
                print(f"简化路径: {original_path} -> {simplified_path}")
                simplified_paths.append(simplified_path)
                path_mapping[simplified_path] = original_path
                file_media_types[simplified_path] = media_type
            else:
                # 如果找不到匹配的媒体库，则使用原路径，默认类型为电影
                print(f"未找到匹配媒体库，使用原路径: {original_path}")
                simplified_paths.append(original_path)
                path_mapping[original_path] = original_path
                file_media_types[original_path] = "movie"  # 默认类型
        
        print(f"正在使用并行方式处理文件名列表，共 {len(simplified_paths)} 个文件")
        
        # 使用新的并行处理方法，使用简化的路径进行Grok识别
        # 传递文件媒体类型给process_filenames_parallel方法
        simplified_results = await new_media_service.process_filenames_parallel(simplified_paths, file_media_types=file_media_types, print_stats=False)
        print(f"并行识别完成，得到 {len(simplified_results)} 个结果")
        
        # 将结果映射回原始路径，并创建路径到结果的映射字典
        results_by_path = {}
        for simplified_path, result in zip(simplified_paths, simplified_results):
            original_path = path_mapping[simplified_path]
            # 确保结果中使用原始路径
            result["original_path"] = original_path
            result["path"] = original_path
            # 使用原始路径作为键存储结果，确保可以正确匹配
            results_by_path[original_path] = result
        
        # 更新文件信息 - 使用路径匹配而不是数组位置
        for file in files:
            # 通过original_path查找对应的结果
            result = results_by_path.get(file.original_path)
            
            # 如果没有找到结果，说明该文件识别失败或没有结果
            if not result:
                print(f"文件 {file.original_path} 没有找到对应的识别结果，跳过处理")
                file.new_name = ""
                file.new_sub_folder = ""
                file.tmdb = None
                continue
            # 只有在成功获取到TMDB ID且没有错误的情况下才生成新文件名
            if "error" not in result and result.get("tmdb_id"):
                # 使用 TMDB 官方中文标题
                chinese_title = result['chinese_title']
                print(f"使用 TMDB 官方中文标题：{chinese_title}")
                
                # 确保同时有TMDB ID和有效的年份
                year = result.get('year')
                if not year or year in ['undefined', 'null', '未知'] or year == '':
                    print(f"文件 {file.original_path} 虽然获取到TMDB ID，但缺少有效年份信息，无法生成标准命名")
                    file.new_name = ""
                    file.new_sub_folder = ""
                    tmdb_info = TMDBInfo(
                        id=str(result['tmdb_id']) if result['tmdb_id'] is not None else None,
                        title=chinese_title if chinese_title is not None else None,
                        original_title=result['english_title'] if result['english_title'] is not None else None,
                        year=None,
                        overview=result.get('overview'),
                        poster_path=result.get('poster_path'),
                        vote_average=result.get('vote_average'),
                        popularity=result.get('popularity')
                    )
                    # Convert TMDBInfo to dict to match FileInfo model expectation
                    try:
                        file.tmdb = tmdb_info.model_dump()  # Pydantic v2
                    except AttributeError:
                        file.tmdb = tmdb_info.dict()  # Pydantic v1
                    file.error = "缺少有效年份信息"
                    continue
                
                # 生成文件夹名（并移除非法路径字符）
                from ..utils.file_utils import sanitize_path_component
                folder_name = sanitize_path_component(
                    f"{chinese_title} ({result['year']}) {{tmdb-{result['tmdb_id']}}}"
                )
                
                # 直接生成文件名而不添加序号
                base_file_name = sanitize_path_component(f"{chinese_title} ({result['year']})")
                file_extension = os.path.splitext(file.original_path)[1]
                file_name = f"{base_file_name}{file_extension}"
                
                print(f"生成的文件夹名：{folder_name}")
                print(f"生成的文件名：{file_name}")
                
                # 创建子目录
                new_path = os.path.join(os.path.dirname(file.original_path), folder_name, file_name)
                print(f"新文件路径：{new_path}")
                
                # 更新文件信息
                file.new_name = file_name
                file.new_sub_folder = folder_name
                tmdb_info = TMDBInfo(
                    id=str(result['tmdb_id']) if result['tmdb_id'] is not None else None,
                    title=chinese_title if chinese_title is not None else None,
                    original_title=result['english_title'] if result['english_title'] is not None else None,
                    year=str(result['year']) if result['year'] is not None else None,
                    overview=result.get('overview'),
                    poster_path=result.get('poster_path'),
                    vote_average=result.get('vote_average'),
                    popularity=result.get('popularity')
                )
                # Convert TMDBInfo to dict to match FileInfo model expectation
                try:
                    file.tmdb = tmdb_info.model_dump()  # Pydantic v2
                except AttributeError:
                    file.tmdb = tmdb_info.dict()  # Pydantic v1
            else:
                # 没有TMDB ID或有错误，不生成新文件名
                print(f"文件 {file.original_path} 未能成功识别，不生成新文件名")
                file.new_name = ""
                file.new_sub_folder = ""
                file.tmdb = None
        
        print("所有文件处理完成")
        
        # 在所有处理完成后最后输出API统计信息
        print("\n\n" + "="*80)
        print("API统计信息汇总 (处理完成)")
        print("="*80)
        new_media_service.grok_api.stats.print_stats()
        new_media_service.tmdb_api.stats.print_stats()
        print("="*80 + "\n")
        
        return {"files": files}
    except Exception as e:
        print(f"处理过程中出错：{str(e)}")
        # 尝试输出统计信息
        try:
            print("\n\n" + "="*80)
            print("API统计信息汇总 (处理出错)")
            print("="*80)
            if 'new_media_service' in locals():
                new_media_service.grok_api.stats.print_stats()
                new_media_service.tmdb_api.stats.print_stats()
            else:
                media_service.grok_api.stats.print_stats()
                media_service.tmdb_api.stats.print_stats()
            print("="*80 + "\n")
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/get_file_details", response_model=FileDetailsResponse)
async def get_file_details(file_details_request: FileDetailsRequest):
    """
    获取文件的详细信息，包括完整路径、创建时间、修改时间和文件大小
    """
    try:
        file_path = file_details_request.file_path
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
            
        # 获取文件状态信息
        file_stat = os.stat(file_path)
        
        # 返回文件详情
        return FileDetailsResponse(
            full_path=file_path,
            creation_time=datetime.fromtimestamp(file_stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
            modification_time=datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            size=file_stat.st_size
        )
    except Exception as e:
        logging.error(f"获取文件详情时出错: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取文件详情失败: {str(e)}")

@router.post("/delete_file", response_model=DeleteFileResponse)
async def delete_file(delete_request: DeleteFileRequest):
    """
    删除指定路径的文件
    """
    try:
        file_path = delete_request.file_path
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
            
        # 检查是否是文件而不是目录
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=400, detail="指定路径不是文件")
            
        # 删除文件
        os.remove(file_path)
        
        # 验证文件是否已删除
        if os.path.exists(file_path):
            return DeleteFileResponse(
                success=False,
                message="文件删除失败，请检查权限"
            )
        
        return DeleteFileResponse(
            success=True,
            message=f"文件 {os.path.basename(file_path)} 已成功删除"
        )
        
    except Exception as e:
        logging.error(f"删除文件时出错: {str(e)}")
        logging.error(traceback.format_exc())
        return DeleteFileResponse(
            success=False,
            message=f"删除文件失败: {str(e)}"
        ) 