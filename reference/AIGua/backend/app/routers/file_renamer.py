"""File renaming router for renaming and organizing media files."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import os
from pydantic import BaseModel
from ..core.config import config_manager
from ..utils.file_utils import safe_rename, safe_makedirs, safe_path_exists, safe_remove_file, safe_get_file_size
import traceback

router = APIRouter(tags=["file_rename"])

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
    selected: bool = True
    new_name: str = ""
    tmdb: Optional[TMDBInfo] = None
    new_sub_folder: str = ""

@router.post("/rename")
async def rename_files(files: List[FileInfo]):
    """Rename the selected files."""
    results = []
    for file in files:
        if file.selected and file.new_name and file.new_sub_folder:
            try:
                original_path = file.original_path
                original_dir = os.path.dirname(original_path)
                
                # 获取媒体库根路径
                media_libraries = config_manager.settings.media_libraries
                library_root = None
                for library in media_libraries:
                    if original_path.startswith(library.path):
                        library_root = library.path
                        break
                
                if not library_root:
                    raise Exception(f"无法确定媒体库根路径: {original_path}")
                
                print(f"媒体库根路径: {library_root}")
                print(f"文件所在目录: {original_dir}")
                
                # 判断文件是否在媒体库根目录下
                is_in_root = original_dir == library_root
                
                # 获取媒体文件扩展名列表
                media_extensions = config_manager.settings.media_extension.split(';')
                
                # 情况1: 如果文件直接位于媒体库根目录下，创建新的子文件夹
                if is_in_root:
                    new_dir = os.path.join(library_root, file.new_sub_folder)
                    print(f"情况1: 文件位于媒体库根目录，将创建新子文件夹: {new_dir}")
                    
                    # 检查目标目录是否已存在
                    if safe_path_exists(new_dir):
                        print(f"警告: 目标文件夹 '{file.new_sub_folder}' 已存在")
                        
                        # 检查目标目录中是否存在大小相同的媒体文件
                        print(f"检查目标目录 {new_dir} 中是否存在重复文件...")
                        
                        # 获取原文件大小
                        original_size = safe_get_file_size(original_path)
                        if original_size <= 0:
                            print(f"无法获取源文件大小，将使用现有文件夹并继续处理")
                        else:
                            # 获取目标目录中的所有媒体文件
                            try:
                                existing_files = os.listdir(new_dir)
                                existing_media_files = [f for f in existing_files 
                                                      if any(f.lower().endswith(ext.lower()) 
                                                             for ext in media_extensions)]
                                
                                # 检查是否有大小相同的文件
                                duplicate_found = False
                                duplicate_file = None
                                new_path_to_check = os.path.join(new_dir, file.new_name)
                                
                                # 首先检查是否已存在完全相同路径的目标文件
                                if safe_path_exists(new_path_to_check):
                                    target_size = safe_get_file_size(new_path_to_check)
                                    if target_size == original_size:
                                        duplicate_found = True
                                        duplicate_file = new_path_to_check
                                
                                # 如果没找到完全匹配的，检查目录中的其他媒体文件
                                if not duplicate_found:
                                    for media_file in existing_media_files:
                                        if media_file == file.new_name:
                                            continue  # 已经检查过这个文件了
                                            
                                        media_file_path = os.path.join(new_dir, media_file)
                                        media_file_size = safe_get_file_size(media_file_path)
                                        
                                        if media_file_size == original_size:
                                            duplicate_found = True
                                            duplicate_file = media_file_path
                                            break
                                
                                if duplicate_found:
                                    print(f"在目标目录中找到了大小相同的媒体文件: {duplicate_file}")
                                    print(f"文件大小: {original_size} 字节")
                                    print(f"检测到重复文件，将删除源文件: {original_path}")
                                    
                                    # 删除源文件
                                    if safe_remove_file(original_path, log_to=results):
                                        print(f"已成功处理重复文件，源文件已被删除")
                                    continue
                            except Exception as e:
                                print(f"检查目标目录中的文件时出错: {e}")
                                print(f"将使用现有文件夹并继续处理")
                    
                    # 使用安全的长路径支持创建目录
                    long_dir = safe_makedirs(new_dir, exist_ok=True)
                    
                    # 构建新的文件路径
                    new_path = os.path.join(new_dir, file.new_name)
                else:
                    # 检查当前子目录的情况
                    current_subdir = original_dir
                    
                    # 统计当前目录及所有子目录中的媒体文件数量（递归检查）
                    media_files_count = 0
                    
                    # 递归遍历所有子目录统计媒体文件
                    for root, _, files in os.walk(current_subdir):
                        for file_name in files:
                            if any(file_name.lower().endswith(ext.lower()) for ext in media_extensions):
                                media_files_count += 1
                    
                    print(f"子目录及其子文件夹中媒体文件总数: {media_files_count}")
                    
                    # 列出当前目录下的文件（用于后续处理字幕文件）
                    subdir_files = os.listdir(current_subdir)
                    
                    # 如果子目录只有一个媒体文件（不包括嵌套子目录中的文件）
                    if media_files_count == 1:
                        # 情况2和3: 子目录只有一个媒体文件，可能有或没有字幕文件
                        print(f"情况2/3: 子目录只有一个媒体文件: {current_subdir}")
                        
                        # 额外安全检查：确认当前处理的文件确实是该目录唯一的媒体文件
                        direct_media_files = [f for f in subdir_files if any(f.lower().endswith(ext.lower()) for ext in media_extensions)]
                        if len(direct_media_files) != 1:
                            print(f"警告: 目录中发现不止一个媒体文件 ({len(direct_media_files)}个)，将采用情况4的处理方式")
                            # 情况4: 创建新的子文件夹
                            new_dir = os.path.join(current_subdir, file.new_sub_folder)
                            print(f"将在当前目录中创建新子文件夹: {new_dir}")
                            
                            if safe_path_exists(new_dir):
                                print(f"警告: 目标文件夹 '{file.new_sub_folder}' 已存在，将使用现有文件夹")
                            
                            # 使用安全的长路径支持创建目录
                            long_dir = safe_makedirs(new_dir, exist_ok=True)
                            
                            # 构建新的文件路径
                            new_path = os.path.join(new_dir, file.new_name)
                            # 跳过字幕文件处理
                            continue
                        
                        # 检查正在处理的文件是否是目录中唯一的媒体文件
                        current_file_name = os.path.basename(original_path)
                        if current_file_name not in direct_media_files:
                            print(f"警告: 当前处理的文件 {current_file_name} 不在目录的媒体文件列表中，将采用情况4的处理方式")
                            # 情况4: 创建新的子文件夹
                            new_dir = os.path.join(current_subdir, file.new_sub_folder)
                            print(f"将在当前目录中创建新子文件夹: {new_dir}")
                            
                            if safe_path_exists(new_dir):
                                print(f"警告: 目标文件夹 '{file.new_sub_folder}' 已存在，将使用现有文件夹")
                            
                            # 使用安全的长路径支持创建目录
                            long_dir = safe_makedirs(new_dir, exist_ok=True)
                            
                            # 构建新的文件路径
                            new_path = os.path.join(new_dir, file.new_name)
                            # 跳过字幕文件处理
                            continue
                        
                        # 重命名子目录为新的子文件夹名
                        parent_dir = os.path.dirname(current_subdir)
                        new_dir = os.path.join(parent_dir, file.new_sub_folder)
                        
                        # 检查目标目录是否已存在
                        if safe_path_exists(new_dir) and current_subdir != new_dir:
                            print(f"警告: 目标文件夹 '{file.new_sub_folder}' 已存在")
                            
                            # 检查目标目录中是否存在大小相同的媒体文件
                            print(f"检查目标目录 {new_dir} 中是否存在重复文件...")
                            
                            # 获取原文件大小
                            original_size = safe_get_file_size(original_path)
                            if original_size <= 0:
                                print(f"无法获取源文件大小，取消重命名操作: {original_path}")
                                results.append({
                                    "file": original_path,
                                    "status": "warning",
                                    "message": f"无法获取源文件大小，取消重命名操作: {original_path}"
                                })
                                continue
                            
                            # 获取目标目录中的所有媒体文件
                            try:
                                existing_files = os.listdir(new_dir)
                                existing_media_files = [f for f in existing_files 
                                                      if any(f.lower().endswith(ext.lower()) 
                                                            for ext in media_extensions)]
                                
                                # 检查是否有大小相同的文件
                                duplicate_found = False
                                duplicate_file = None
                                
                                for media_file in existing_media_files:
                                    media_file_path = os.path.join(new_dir, media_file)
                                    media_file_size = safe_get_file_size(media_file_path)
                                    
                                    if media_file_size == original_size:
                                        duplicate_found = True
                                        duplicate_file = media_file_path
                                        break
                                
                                if duplicate_found:
                                    print(f"在目标目录中找到了大小相同的媒体文件: {duplicate_file}")
                                    print(f"文件大小: {original_size} 字节")
                                    print(f"检测到重复文件，将删除源文件: {original_path}")
                                    
                                    # 删除源文件
                                    if safe_remove_file(original_path, log_to=results):
                                        print(f"已成功处理重复文件，源文件已被删除")
                                    continue
                                else:
                                    print(f"目标目录中没有找到大小相同的媒体文件，文件可能不相同")
                                    print(f"源文件大小: {original_size} 字节")
                                    print(f"目标目录已存在且没有重复文件，取消重命名操作: {new_dir}")
                                    results.append({
                                        "file": original_path,
                                        "status": "warning",
                                        "message": f"目标目录已存在且没有发现重复文件，取消重命名操作: {new_dir}"
                                    })
                                    continue
                            except Exception as e:
                                print(f"检查目标目录中的文件时出错: {e}")
                                print(f"取消重命名操作: {new_dir}")
                                results.append({
                                    "file": original_path,
                                    "status": "warning",
                                    "message": f"检查目标目录时出错，取消重命名操作: {new_dir}"
                                })
                                continue
                        
                        # 如果当前目录名与新目录名不同，则重命名目录
                        if current_subdir != new_dir:
                            try:
                                # 使用长路径支持重命名目录
                                if safe_rename(current_subdir, new_dir):
                                    print(f"已重命名子目录: {current_subdir} -> {new_dir}")
                                    
                                    # 重命名目录成功后，更新原始文件路径以反映新的目录结构
                                    current_file_name = os.path.basename(original_path)
                                    original_path = os.path.join(new_dir, current_file_name)
                                    print(f"更新原始文件路径: {original_path}")
                                else:
                                    # 目录重命名失败，改为创建新目录
                                    print(f"子目录重命名失败，将创建新目录: {new_dir}")
                                    safe_makedirs(new_dir, exist_ok=True)
                                    # 后续将文件移动到新目录
                            except Exception as e:
                                print(f"重命名子目录失败: {e}")
                                # 创建新目录作为备用方案
                                safe_makedirs(new_dir, exist_ok=True)
                        
                        # 构建新的文件路径
                        new_path = os.path.join(new_dir, file.new_name)
                        
                        # 情况3: 处理字幕文件等附属文件
                        subtitle_extensions = ['.srt', '.ass', '.ssa', '.sub', '.idx', '.vtt']
                        
                        # 如果已经重命名了目录，需要重新获取目录中的文件列表
                        if current_subdir != new_dir:
                            try:
                                # 获取新目录中的文件
                                subdir_files = os.listdir(new_dir)
                                print(f"已更新子目录文件列表 (包含 {len(subdir_files)} 个文件)")
                                # 重新获取媒体文件列表
                                direct_media_files = [f for f in subdir_files if any(f.lower().endswith(ext.lower()) for ext in media_extensions)]
                            except Exception as e:
                                print(f"无法读取新目录内容: {e}")
                                # 如果读取新目录失败，使用空列表避免错误
                                subdir_files = []
                                direct_media_files = []
                        
                        # 筛选出非媒体文件（字幕等）
                        other_files = [f for f in subdir_files if f not in direct_media_files]
                        
                        media_file_basename = os.path.splitext(os.path.basename(original_path))[0]
                        new_media_basename = os.path.splitext(file.new_name)[0]
                        
                        for other_file in other_files:
                            other_file_path = os.path.join(current_subdir, other_file)
                            
                            # 如果已经重命名了目录，更新路径
                            if current_subdir != new_dir:
                                other_file_path = os.path.join(new_dir, other_file)
                            
                            # 检查是否为字幕文件或其他附属文件
                            _, other_ext = os.path.splitext(other_file)
                            if other_ext.lower() in subtitle_extensions:
                                # 重命名字幕文件，保持扩展名不变
                                new_other_name = f"{new_media_basename}{other_ext}"
                                new_other_path = os.path.join(new_dir, new_other_name)
                                
                                # 确保不会覆盖自身
                                if other_file_path != new_other_path and safe_path_exists(other_file_path):
                                    # 检查目标字幕文件是否已存在
                                    if safe_path_exists(new_other_path):
                                        # 比较文件大小判断是否为重复文件
                                        original_size = safe_get_file_size(other_file_path)
                                        target_size = safe_get_file_size(new_other_path)
                                        
                                        if original_size > 0 and target_size > 0 and original_size == target_size:
                                            print(f"目标字幕文件已存在且文件大小相同 ({original_size} 字节)，判定为重复字幕")
                                            print(f"将删除源字幕文件: {other_file_path}")
                                            
                                            # 删除源字幕文件
                                            if safe_remove_file(other_file_path):
                                                print(f"检测到重复字幕文件，已删除源文件: {other_file_path}")
                                            else:
                                                print(f"检测到重复字幕文件，但删除源文件失败: {other_file_path}")
                                            continue
                                        else:
                                            # 字幕文件大小不同，视为不同文件，跳过处理
                                            print(f"目标字幕文件已存在且文件大小不同，跳过处理: {other_file_path}")
                                            continue
                                    
                                    try:
                                        # 使用长路径支持重命名附属文件
                                        if safe_rename(other_file_path, new_other_path):
                                            print(f"已重命名附属文件: {other_file_path} -> {new_other_path}")
                                        else:
                                            print(f"重命名附属文件失败: {other_file_path}")
                                    except Exception as e:
                                        print(f"重命名附属文件失败: {other_file_path} -> {new_other_path}, 错误: {e}")
                    else:
                        # 情况4: 子目录有多个媒体文件，创建新的子文件夹
                        print(f"情况4: 子目录及其子文件夹中有多个媒体文件 ({media_files_count}个)，将在其中创建新子文件夹: {current_subdir}")
                        new_dir = os.path.join(current_subdir, file.new_sub_folder)
                        
                        # 检查目标目录是否已存在
                        if safe_path_exists(new_dir):
                            print(f"警告: 目标文件夹 '{file.new_sub_folder}' 已存在")
                            
                            # 检查目标目录中是否存在大小相同的媒体文件
                            print(f"检查目标目录 {new_dir} 中是否存在重复文件...")
                            
                            # 获取原文件大小
                            original_size = safe_get_file_size(original_path)
                            if original_size <= 0:
                                print(f"无法获取源文件大小，将使用现有文件夹并继续处理")
                            else:
                                # 获取目标目录中的所有媒体文件
                                try:
                                    existing_files = os.listdir(new_dir)
                                    existing_media_files = [f for f in existing_files 
                                                          if any(f.lower().endswith(ext.lower()) 
                                                                for ext in media_extensions)]
                                    
                                    # 检查是否有大小相同的文件
                                    duplicate_found = False
                                    duplicate_file = None
                                    new_path_to_check = os.path.join(new_dir, file.new_name)
                                    
                                    # 首先检查是否已存在完全相同路径的目标文件
                                    if safe_path_exists(new_path_to_check):
                                        target_size = safe_get_file_size(new_path_to_check)
                                        if target_size == original_size:
                                            duplicate_found = True
                                            duplicate_file = new_path_to_check
                                    
                                    # 如果没找到完全匹配的，检查目录中的其他媒体文件
                                    if not duplicate_found:
                                        for media_file in existing_media_files:
                                            if media_file == file.new_name:
                                                continue  # 已经检查过这个文件了
                                                
                                            media_file_path = os.path.join(new_dir, media_file)
                                            media_file_size = safe_get_file_size(media_file_path)
                                            
                                            if media_file_size == original_size:
                                                duplicate_found = True
                                                duplicate_file = media_file_path
                                                break
                                    
                                    if duplicate_found:
                                        print(f"在目标目录中找到了大小相同的媒体文件: {duplicate_file}")
                                        print(f"文件大小: {original_size} 字节")
                                        print(f"检测到重复文件，将删除源文件: {original_path}")
                                        
                                        # 删除源文件
                                        if safe_remove_file(original_path, log_to=results):
                                            print(f"已成功处理重复文件，源文件已被删除")
                                        continue
                                except Exception as e:
                                    print(f"检查目标目录中的文件时出错: {e}")
                                    print(f"将使用现有文件夹并继续处理")
                        
                        # 使用安全的长路径支持创建目录
                        long_dir = safe_makedirs(new_dir, exist_ok=True)
                        
                        # 构建新的文件路径
                        new_path = os.path.join(new_dir, file.new_name)
                
                # 处理目标文件已存在的情况
                if safe_path_exists(new_path) and original_path != new_path:
                    # 比较文件大小判断是否为重复文件
                    original_size = safe_get_file_size(original_path)
                    target_size = safe_get_file_size(new_path)
                    
                    if original_size > 0 and target_size > 0 and original_size == target_size:
                        print(f"目标文件已存在且文件大小相同 ({original_size} 字节)，判定为重复文件")
                        print(f"将删除源文件并终止重命名操作: {original_path}")
                        
                        # 删除源文件
                        if safe_remove_file(original_path, log_to=results):
                            print(f"已成功处理重复文件，源文件已被删除")
                        continue
                    else:
                        # 文件大小不同，视为不同文件，放弃重命名
                        print(f"目标文件已存在且文件大小不同 (源: {original_size}, 目标: {target_size} 字节)")
                        print(f"文件被视为不同文件，取消重命名操作: {original_path}")
                        results.append({
                            "file": original_path,
                            "status": "warning",
                            "message": f"目标文件已存在，且文件大小不同，取消重命名: {original_path}"
                        })
                        continue
                
                # 如果源文件和目标文件不同，则进行重命名
                if original_path != new_path:
                    # 首先检查源文件是否存在
                    if safe_path_exists(original_path):
                        print(f"找到源文件，准备重命名: {original_path}")
                        # 使用长路径支持重命名文件
                        if safe_rename(original_path, new_path):
                            results.append({
                                "file": original_path,
                                "status": "success",
                                "message": f"文件已成功重命名并移动到新位置：{new_path}"
                            })
                        else:
                            results.append({
                                "file": original_path,
                                "status": "error",
                                "message": f"文件重命名失败: {original_path} -> {new_path}"
                            })
                    else:
                        # 源文件不存在，检查目标文件是否已存在（可能已经重命名但路径记录未更新）
                        if safe_path_exists(new_path):
                            print(f"源文件不存在但目标文件已存在，可能已被重命名: {new_path}")
                            results.append({
                                "file": original_path,
                                "status": "success",
                                "message": f"文件可能已重命名至：{new_path}"
                            })
                        else:
                            print(f"源文件不存在，跳过重命名操作: {original_path}")
                            results.append({
                                "file": original_path,
                                "status": "warning",
                                "message": f"文件不存在，无法重命名: {original_path}"
                            })
                else:
                    print(f"源文件和目标文件路径相同，无需重命名: {original_path}")
                    results.append({
                        "file": original_path,
                        "status": "warning",
                        "message": f"文件路径未变更: {original_path}"
                    })
            except Exception as e:
                error_msg = f"重命名文件失败: {str(e)}"
                print(error_msg)
                print(f"错误类型: {type(e)}")
                print(f"错误堆栈: {traceback.format_exc()}")
                results.append({
                    "file": file.original_path,
                    "status": "error",
                    "message": error_msg
                })
    
    # 统计各种状态的结果
    success_count = sum(1 for r in results if r["status"] == "success")
    warning_count = sum(1 for r in results if r["status"] == "warning")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    return {
        "message": f"重命名操作已完成：{success_count}个成功，{warning_count}个未变更，{error_count}个失败",
        "results": results,
        "success": success_count,
        "warnings": warning_count,
        "errors": error_count
    } 