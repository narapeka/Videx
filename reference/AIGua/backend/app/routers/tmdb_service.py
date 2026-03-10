"""TMDB service router for searching and retrieving movie information."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import os
from pydantic import BaseModel
from ..core.config import config_manager
from ..services.api import TMDBAPI
import asyncio
import traceback
import re

router = APIRouter(tags=["tmdb_service"])

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

class SearchTMDBRequest(BaseModel):
    query: str
    year: str = None
    language: str = None
    file_path: str
    movie_id: int = None  # Optional movie ID if a specific movie is selected

# 新增请求模型，用于根据ID获取电影信息
class GetMovieByIdRequest(BaseModel):
    movie_id: int
    file_path: str  # 需要文件路径用于生成新文件名

# 新增请求模型，用于根据IMDB ID获取电影信息
class FindByImdbIdRequest(BaseModel):
    imdb_id: str  # IMDB ID，格式为 tt开头的字符串
    file_path: str  # 需要文件路径用于生成新文件名

@router.post("/search_tmdb")
async def search_tmdb(request: SearchTMDBRequest):
    """Search TMDB for a movie by title and year."""
    try:
        query = request.query
        year = request.year
        file_path = request.file_path
        language = request.language
        movie_id = request.movie_id
        
        print(f"手动搜索TMDB: 查询={query}, 年份={year}, 语言={language}, 文件路径={file_path}, 电影ID={movie_id}")
        
        if not file_path:
            print("错误: 缺少文件路径参数")
            raise HTTPException(status_code=400, detail="缺少文件路径参数")
        
        # 重新加载配置以应用最新的速率限制设置
        current_settings = config_manager.refresh_settings()
        print(f"使用刷新后的配置: tmdb_rate_limit={current_settings.tmdb_rate_limit}")
        
        # 初始化 TMDB API 服务
        tmdb_api = TMDBAPI()
        
        # 如果提供了电影ID，直接获取该电影
        if movie_id:
            movie = await tmdb_api.get_movie_by_id(movie_id)
            if not movie:
                # 输出TMDB API统计信息
                print("\n" + "="*80)
                print("TMDB API统计信息 (未找到电影)")
                print("="*80)
                tmdb_api.stats.print_stats()
                print("="*80 + "\n")
                return {"success": False, "message": f"未找到ID为 {movie_id} 的电影"}
                
            # 确保所有必要的字段都存在且不为None
            tmdb_id = movie.get("id")
            chinese_title = movie.get("title")
            english_title = movie.get("original_title")
            year = movie.get("year")
            
            if not all([tmdb_id, chinese_title, english_title, year]):
                print(f"电影数据不完整: {movie}")
                return {"success": False, "message": f"电影数据不完整，ID为 {movie_id} 的电影缺少必要信息"}
            
            # 若标题不含中文，从 TMDB alternative_titles/translations 取中文名（与 aigua.tv 一致）
            if chinese_title and not tmdb_api.is_chinese(chinese_title):
                chinese_title = await tmdb_api.get_chinese_title_for_movie(chinese_title, movie_id)
                if tmdb_api.is_chinese(chinese_title):
                    print(f"使用 TMDB 中文名: {chinese_title}")
            
            # 将单个电影转换为搜索结果格式（与常规搜索结果格式一致）
            movie_as_result = {
                "id": tmdb_id,
                "title": chinese_title,
                "original_title": english_title,
                "release_date": year,
                "year": year,
                "overview": movie.get("overview", ""),
                "poster_path": movie.get("poster_path", ""),
                "vote_average": movie.get("vote_average", 0),
                "popularity": movie.get("popularity", 0)
            }
            
            # 输出TMDB API统计信息
            print("\n" + "="*80)
            print("TMDB API统计信息 (通过ID获取电影成功)")
            print("="*80)
            tmdb_api.stats.print_stats()
            print("="*80 + "\n")
            
            # 返回标准的搜索结果格式，但只包含一个结果
            return {
                "success": True,
                "results": [movie_as_result]  # 注意使用一致的响应格式
            }
            
        # 否则搜索电影
        if not query:
            raise HTTPException(status_code=400, detail="缺少查询参数")
            
        # 检查查询字符串中是否包含IMDB ID
        imdb_id_match = re.search(r'\b(tt\d{6,8})\b', query)
        
        if imdb_id_match:
            # 找到了IMDB ID，使用find_by_external_id搜索
            imdb_id = imdb_id_match.group(1)
            print(f"在查询中检测到IMDB ID: {imdb_id}，使用IMDB ID搜索")
            
            # 调用find_by_external_id方法
            movie = await tmdb_api.find_by_external_id(imdb_id, "imdb_id")
            
            if not movie:
                # 输出TMDB API统计信息
                print("\n" + "="*80)
                print(f"TMDB API统计信息 (未找到IMDB电影): IMDB ID={imdb_id}")
                print("="*80)
                tmdb_api.stats.print_stats()
                print("="*80 + "\n")
                
                # 如果IMDB ID搜索失败，尝试使用常规搜索
                print(f"IMDB ID搜索失败，尝试使用常规搜索: {query}")
                if year and year.strip():
                    movies = await tmdb_api.search_movie(query, year, language)
                else:
                    movies = await tmdb_api.search_movie(query, language=language)
                
                if not movies:
                    print("\n" + "="*80)
                    print("TMDB API统计信息 (常规搜索也无结果)")
                    print("="*80)
                    tmdb_api.stats.print_stats()
                    print("="*80 + "\n")
                    return {"success": False, "message": "未找到匹配的电影"}
                    
                # 返回常规搜索结果列表
                print("\n" + "="*80)
                print("TMDB API统计信息 (IMDB ID搜索失败但常规搜索成功)")
                print("="*80)
                tmdb_api.stats.print_stats()
                print("="*80 + "\n")
                
                return {
                    "success": True,
                    "results": movies
                }
            
            # IMDB ID搜索成功 - 但我们需要将其转换为与常规搜索相同的结果格式以保持一致性
            # 确保所有必要的字段都存在且不为None
            tmdb_id = movie.get("id")
            chinese_title = movie.get("title")
            english_title = movie.get("original_title")
            year = movie.get("year")
            
            if not all([tmdb_id, chinese_title, english_title, year]):
                print(f"IMDB电影数据不完整: {movie}")
                
                # 如果IMDB ID搜索返回不完整数据，尝试使用常规搜索
                print(f"IMDB ID搜索返回不完整数据，尝试使用常规搜索: {query}")
                if year and year.strip():
                    movies = await tmdb_api.search_movie(query, year, language)
                else:
                    movies = await tmdb_api.search_movie(query, language=language)
                
                if not movies:
                    print("\n" + "="*80)
                    print("TMDB API统计信息 (常规搜索也无结果)")
                    print("="*80)
                    tmdb_api.stats.print_stats()
                    print("="*80 + "\n")
                    return {"success": False, "message": "未找到匹配的电影"}
                    
                # 返回常规搜索结果列表
                print("\n" + "="*80)
                print("TMDB API统计信息 (IMDB ID搜索数据不完整但常规搜索成功)")
                print("="*80)
                tmdb_api.stats.print_stats()
                print("="*80 + "\n")
                
                return {
                    "success": True,
                    "results": movies
                }
            
            # 将单个电影转换为搜索结果格式（与常规搜索结果格式一致）
            movie_as_result = {
                "id": tmdb_id,
                "title": chinese_title,
                "original_title": english_title,
                "release_date": year,
                "year": year,
                "overview": movie.get("overview", ""),
                "poster_path": movie.get("poster_path", ""),
                "vote_average": movie.get("vote_average", 0),
                "popularity": movie.get("popularity", 0)
            }
            
            # 输出TMDB API统计信息
            print("\n" + "="*80)
            print(f"TMDB API统计信息 (通过IMDB ID搜索成功): IMDB ID={imdb_id}")
            print("="*80)
            tmdb_api.stats.print_stats()
            print("="*80 + "\n")
            
            # 返回标准的搜索结果格式，但只包含一个结果
            return {
                "success": True,
                "results": [movie_as_result]  # 注意这里改为返回结果数组，保持与常规搜索相同的格式
            }
        
        # 常规电影搜索
        if year and year.strip():
            movies = await tmdb_api.search_movie(query, year, language)
        else:
            movies = await tmdb_api.search_movie(query, language=language)
        
        if not movies:
            # 输出TMDB API统计信息
            print("\n" + "="*80)
            print("TMDB API统计信息 (搜索无结果)")
            print("="*80)
            tmdb_api.stats.print_stats()
            print("="*80 + "\n")
            return {"success": False, "message": "未找到匹配的电影"}
            
        # 输出TMDB API统计信息
        print("\n" + "="*80)
        print("TMDB API统计信息 (搜索成功)")
        print("="*80)
        tmdb_api.stats.print_stats()
        print("="*80 + "\n")
            
        # 返回搜索结果列表
        return {
            "success": True,
            "results": movies
        }
    except Exception as e:
        print(f"搜索TMDB时出错: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 尝试输出统计信息（如果API已初始化）
        try:
            if 'tmdb_api' in locals():
                print("\n" + "="*80)
                print("TMDB API统计信息 (搜索出错)")
                print("="*80)
                tmdb_api.stats.print_stats()
                print("="*80 + "\n")
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

# 新增端点，专门用于根据ID获取电影信息
@router.post("/get_movie_by_id")
async def get_movie_by_id(request: GetMovieByIdRequest):
    """Get movie information by TMDB ID."""
    try:
        movie_id = request.movie_id
        file_path = request.file_path
        
        print(f"根据ID获取电影信息: ID={movie_id}, 文件路径={file_path}")
        
        if not file_path:
            print("错误: 缺少文件路径参数")
            raise HTTPException(status_code=400, detail="缺少文件路径参数")
        
        # 重新加载配置以应用最新的速率限制设置
        current_settings = config_manager.refresh_settings()
        print(f"使用刷新后的配置: tmdb_rate_limit={current_settings.tmdb_rate_limit}")
        
        # 初始化 TMDB API 服务
        tmdb_api = TMDBAPI()
        
        # 获取电影信息
        movie = await tmdb_api.get_movie_by_id(movie_id)
        if not movie:
            # 输出TMDB API统计信息
            print("\n" + "="*80)
            print("TMDB API统计信息 (未找到电影)")
            print("="*80)
            tmdb_api.stats.print_stats()
            print("="*80 + "\n")
            return {"success": False, "message": f"未找到ID为 {movie_id} 的电影"}
        
        # 确保所有必要的字段都存在且不为None
        tmdb_id = movie.get("id")
        chinese_title = movie.get("title")
        english_title = movie.get("original_title")
        year = movie.get("year")
        
        if not all([tmdb_id, chinese_title, english_title, year]):
            print(f"电影数据不完整: {movie}")
            return {"success": False, "message": f"电影数据不完整，ID为 {movie_id} 的电影缺少必要信息"}
        
        # 若标题不含中文，从 TMDB alternative_titles/translations 取中文名（与 aigua.tv 一致）
        if chinese_title and not tmdb_api.is_chinese(chinese_title):
            movie_id_int = int(movie_id) if isinstance(movie_id, str) else movie_id
            chinese_title = await tmdb_api.get_chinese_title_for_movie(chinese_title, movie_id_int)
            if tmdb_api.is_chinese(chinese_title):
                print(f"使用 TMDB 中文名: {chinese_title}")
        
        print(f"成功获取电影信息: ID={tmdb_id}, 中文名={chinese_title}, 英文名={english_title}, 年份={year}")
        
        # 将单个电影转换为搜索结果格式（与常规搜索结果格式一致）
        movie_as_result = {
            "id": tmdb_id,
            "title": chinese_title,
            "original_title": english_title,
            "release_date": year,
            "year": year,
            "overview": movie.get("overview", ""),
            "poster_path": movie.get("poster_path", ""),
            "vote_average": movie.get("vote_average", 0),
            "popularity": movie.get("popularity", 0)
        }
        
        # 输出TMDB API统计信息
        print("\n" + "="*80)
        print("TMDB API统计信息 (获取电影成功)")
        print("="*80)
        tmdb_api.stats.print_stats()
        print("="*80 + "\n")
        
        # 返回标准的搜索结果格式，但只包含一个结果
        return {
            "success": True,
            "results": [movie_as_result]  # 注意使用一致的响应格式
        }
    except Exception as e:
        print(f"根据ID获取电影信息时出错: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 尝试输出统计信息（如果API已初始化）
        try:
            if 'tmdb_api' in locals():
                print("\n" + "="*80)
                print("TMDB API统计信息 (获取电影出错)")
                print("="*80)
                tmdb_api.stats.print_stats()
                print("="*80 + "\n")
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/find_by_imdb_id")
async def find_by_imdb_id(request: FindByImdbIdRequest):
    """Find a movie using IMDB ID through TMDB's Find API."""
    try:
        imdb_id = request.imdb_id
        file_path = request.file_path
        
        print(f"根据IMDB ID获取电影信息: IMDB ID={imdb_id}, 文件路径={file_path}")
        
        if not file_path:
            print("错误: 缺少文件路径参数")
            raise HTTPException(status_code=400, detail="缺少文件路径参数")
        
        if not imdb_id or not imdb_id.startswith('tt'):
            print(f"错误: 无效的IMDB ID格式: {imdb_id}")
            raise HTTPException(status_code=400, detail="无效的IMDB ID格式，应以'tt'开头")
        
        # 重新加载配置以应用最新的速率限制设置
        current_settings = config_manager.refresh_settings()
        print(f"使用刷新后的配置: tmdb_rate_limit={current_settings.tmdb_rate_limit}")
        
        # 初始化 TMDB API 服务
        tmdb_api = TMDBAPI()
        
        # 调用 Find by ID API 获取电影信息
        print(f"开始调用TMDB查找服务: imdb_id={imdb_id}")
        movie = await tmdb_api.find_by_external_id(imdb_id, "imdb_id")
        print(f"TMDB Find API 返回结果: {movie}")
        
        if not movie:
            # 输出TMDB API统计信息
            print("\n" + "="*80)
            print(f"TMDB API统计信息 (未找到电影): IMDB ID={imdb_id}")
            print("="*80)
            tmdb_api.stats.print_stats()
            print("="*80 + "\n")
            return {"success": False, "message": f"未找到IMDB ID为 {imdb_id} 的电影"}
        
        # 确保所有必要的字段都存在且不为None
        tmdb_id = movie.get("id")
        chinese_title = movie.get("title")
        english_title = movie.get("original_title")
        year = movie.get("year")
        
        if not all([tmdb_id, chinese_title, english_title, year]):
            print(f"IMDB电影数据不完整: {movie}")
            return {"success": False, "message": f"电影数据不完整，IMDB ID为 {imdb_id} 的电影缺少必要信息"}
        
        # 若标题不含中文，从 TMDB alternative_titles/translations 取中文名（与 aigua.tv 一致）
        if chinese_title and not tmdb_api.is_chinese(chinese_title):
            movie_id_int = int(tmdb_id) if isinstance(tmdb_id, str) else tmdb_id
            chinese_title = await tmdb_api.get_chinese_title_for_movie(chinese_title, movie_id_int)
            if tmdb_api.is_chinese(chinese_title):
                print(f"使用 TMDB 中文名: {chinese_title}")
        
        print(f"成功获取电影信息: ID={tmdb_id}, 中文名={chinese_title}, 英文名={english_title}, 年份={year}")
        
        # 将单个电影转换为搜索结果格式（与常规搜索结果格式一致）
        movie_as_result = {
            "id": tmdb_id,
            "title": chinese_title,
            "original_title": english_title,
            "release_date": year,
            "year": year,
            "overview": movie.get("overview", ""),
            "poster_path": movie.get("poster_path", ""),
            "vote_average": movie.get("vote_average", 0),
            "popularity": movie.get("popularity", 0)
        }
        
        # 输出TMDB API统计信息
        print("\n" + "="*80)
        print("TMDB API统计信息 (通过IMDB ID获取电影成功)")
        print("="*80)
        tmdb_api.stats.print_stats()
        print("="*80 + "\n")
        
        # 返回标准的搜索结果格式，但只包含一个结果
        return {
            "success": True,
            "results": [movie_as_result]  # 注意使用一致的响应格式
        }
    except Exception as e:
        print(f"根据IMDB ID获取电影信息时出错: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        # 尝试输出统计信息（如果API已初始化）
        try:
            if 'tmdb_api' in locals():
                print("\n" + "="*80)
                print("TMDB API统计信息 (获取电影出错)")
                print("="*80)
                tmdb_api.stats.print_stats()
                print("="*80 + "\n")
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e)) 