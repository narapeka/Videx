import aiohttp
import json
import re
import ssl
from typing import Dict, List, Optional
from ..core.config import settings
import logging
import asyncio
import time
import traceback

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 添加API性能统计类
class APIStats:
    def __init__(self, api_name):
        self.api_name = api_name
        self.call_count = 0
        self.total_time = 0
        self.times = []
        self.error_count = 0
        self.rate_limit_errors = 0
    
    def add_call(self, duration):
        self.call_count += 1
        self.total_time += duration
        self.times.append(duration)
    
    def add_error(self, is_rate_limit=False):
        self.error_count += 1
        if is_rate_limit:
            self.rate_limit_errors += 1
    
    def get_avg_time(self):
        if self.call_count == 0:
            return 0
        return self.total_time / self.call_count
    
    def print_stats(self):
        avg_time = self.get_avg_time()
        print(f"\n{'-'*50}")
        print(f"{self.api_name} API 调用统计:")
        print(f"总调用次数: {self.call_count}")
        print(f"总耗时: {self.total_time:.2f} 秒")
        print(f"平均耗时: {avg_time:.2f} 秒")
        print(f"错误次数: {self.error_count}")
        print(f"速率限制错误: {self.rate_limit_errors}")
        print(f"{'-'*50}\n")

# 新增速率限制器类
class RateLimiter:
    def __init__(self, rate_limit):
        """初始化速率限制器
        
        Args:
            rate_limit: 每秒允许的最大请求数量
        """
        self.rate_limit = rate_limit
        self.tokens = rate_limit  # 令牌桶中的令牌数量
        self.last_refill = time.time()  # 上次补充令牌的时间
        self.lock = asyncio.Lock()  # 用于令牌桶同步的锁
    
    async def acquire(self):
        """尝试获取一个令牌，速率限制控制
        
        Returns:
            bool: 是否成功获取令牌
        """
        async with self.lock:
            # 计算应补充的令牌数量
            now = time.time()
            time_passed = now - self.last_refill
            tokens_to_add = time_passed * self.rate_limit
            
            # 补充令牌，但不超过最大限制
            self.tokens = min(self.rate_limit, self.tokens + tokens_to_add)
            self.last_refill = now
            
            # 尝试获取令牌
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                return False
    
    async def wait_for_token(self):
        """等待直到能够获取令牌"""
        while True:
            if await self.acquire():
                return
            # 如果没有获取到令牌，等待一小段时间
            wait_time = 1.0 / self.rate_limit
            await asyncio.sleep(wait_time)

class GrokAPI:
    def __init__(self):
        # 从配置管理器获取最新配置，而不是直接使用settings
        from ..core.config import config_manager
        current_settings = config_manager.settings
        
        self.api_key = current_settings.grok_api_key
        self.base_url = "https://api.x.ai/v1"  # 修改为正确的API地址
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # 设置代理
        self.proxy = f"http://{current_settings.proxy_url.strip()}" if current_settings.proxy_url else None
        # 设置速率限制器
        self.rate_limiter = RateLimiter(current_settings.grok_rate_limit)
        logging.info(f"GrokAPI 代理设置: {self.proxy}")
        logging.info(f"GrokAPI 基础URL: {self.base_url}")
        logging.info(f"GrokAPI 速率限制: {current_settings.grok_rate_limit} 请求/秒")
        # 初始化统计对象
        self.stats = APIStats("Grok")

    async def parse_single_filename_batch(self, filenames: List[str], file_media_types: dict = None) -> List[Dict]:
        """Parse a batch of filenames using Grok API."""
        try:
            logging.info(f"正在调用Grok API，处理 {len(filenames)} 个文件名")
            
            # 等待获取令牌，速率控制
            await self.rate_limiter.wait_for_token()
            
            # 开始计时
            start_time = time.time()
            
            # 检查文件类型，默认所有文件为电影类型
            if file_media_types is None:
                file_media_types = {filename: "movie" for filename in filenames}
            
            # 确定此批次文件的主要类型（movie或tv）
            media_types = list(file_media_types.values())
            is_movie_batch = all(media_type == "movie" for media_type in media_types)
            is_tv_batch = all(media_type == "tv" for media_type in media_types)
            
            # 规定 Grok 必须返回的 JSON 结构，便于解析
            json_format_instruction = (
                '你必须只返回一个 JSON 对象，不要返回任何其他文字或说明。'
                '格式：{"movies": [{"chinese_name": "中文标题", "english_name": "English title", "year": 2002}, ...]}。'
                '要求：movies 为数组，长度必须与输入文件数量相同，且顺序与输入一一对应；'
                '每项仅含三个字段（英文键名）：chinese_name、english_name、year（年份为数字或空字符串）。'
            )
            # 根据媒体类型构建提示词
            if is_movie_batch:
                system_prompt = (
                    "你是一个专业的电影信息解析助手。请解析电影文件名，只关注电影，不要解析电视剧。"
                    + json_format_instruction
                )
                user_prompt = "请解析以下电影文件名，按顺序为每个文件返回一条记录。\n\n"
            elif is_tv_batch:
                system_prompt = (
                    "你是一个专业的电视剧信息解析助手。请解析电视剧文件名，只关注电视剧，不要解析电影。"
                    + json_format_instruction.replace('"movies"', '"tv_shows"')
                )
                user_prompt = "请解析以下电视剧文件名，按顺序为每个文件返回一条记录。\n\n"
            else:
                # 混合类型批次
                system_prompt = (
                    "你是一个专业的视频信息解析助手。请解析文件名（电影或电视剧）。"
                    + json_format_instruction.replace('"movies"', '"items"')
                )
                user_prompt = "请解析以下视频文件名，按顺序为每个文件返回一条记录。\n\n"
                
            # 添加文件名到提示词
            for i, filename in enumerate(filenames, 1):
                media_type = file_media_types.get(filename, "movie")  # 默认为电影
                media_type_text = "电影" if media_type == "movie" else "电视剧"
                user_prompt += f"{i}. {filename} (类型: {media_type_text})\n"
            
            payload = {
                "model": "grok-4-fast-non-reasoning",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            }
            
            logging.info(f"发送到 Grok API 的请求：{json.dumps(payload, ensure_ascii=False)}")
            
            # 使用更宽松的 SSL 设置
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        async with session.post(
                            f"{self.base_url}/chat/completions",
                            headers=self.headers,
                            json=payload,
                            proxy=self.proxy,
                            timeout=30
                        ) as response:
                            logging.info(f"Grok API响应状态码: {response.status}")
                            
                            # 处理速率限制
                            if response.status == 429:
                                error_text = await response.text()
                                retry_after = response.headers.get("Retry-After", "1")
                                try:
                                    retry_seconds = int(retry_after)
                                except:
                                    retry_seconds = 1
                                
                                logging.error(f"Grok API 速率限制错误(429): {error_text}. 将在 {retry_seconds} 秒后重试.")
                                self.stats.add_error(is_rate_limit=True)
                                
                                # 更新速率限制器
                                self.rate_limiter = RateLimiter(settings.grok_rate_limit / 2)  # 减半速率
                                
                                # 等待指定的时间
                                await asyncio.sleep(retry_seconds)
                                retry_count += 1
                                continue
                                
                            if response.status != 200:
                                error_text = await response.text()
                                logging.error(f"Grok API 错误响应: {error_text}")
                                self.stats.add_error()
                                raise Exception(f"API调用失败: {response.status}, {error_text}")
                            
                            response.raise_for_status()
                            result = await response.json()
                            
                            # 结束计时并记录统计信息
                            end_time = time.time()
                            self.stats.add_call(end_time - start_time)
                            
                            # 解析API返回的内容
                            try:
                                content = result['choices'][0]['message']['content']
                                logging.info(f"Grok API 返回内容: {content}")
                                
                                # 尝试从返回的文本中提取JSON部分
                                start_idx = content.find('[')  # 先尝试查找数组
                                end_idx = content.rfind(']') + 1
                                if start_idx == -1 or end_idx == 0:
                                    # 如果找不到数组，尝试查找对象
                                    start_idx = content.find('{')
                                    end_idx = content.rfind('}') + 1
                                
                                if start_idx != -1 and end_idx != 0:
                                    json_str = content[start_idx:end_idx]
                                    logging.info(f"提取的JSON字符串: {json_str}")
                                    
                                    # 清理JSON字符串
                                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                                    json_str = json_str.replace('\\n', ' ').replace('\\r', '')
                                    json_str = json_str.replace('\\t', ' ')
                                    json_str = ' '.join(json_str.split())  # 移除多余空格
                                    
                                    # 尝试修复常见的JSON格式问题
                                    json_str = json_str.replace('，', ',')
                                    json_str = json_str.replace('：', ':')
                                    json_str = json_str.replace('"', '"').replace('"', '"')
                                    json_str = json_str.replace(''', "'").replace(''', "'")
                                    
                                    try:
                                        parsed_data = json.loads(json_str)
                                        # 确保 parsed_data 是列表，支持多种 Grok 返回格式
                                        if isinstance(parsed_data, dict):
                                            # 格式1: {"movies": [...]} / {"tv_shows": [...]} / {"items": [...]}（与 prompt 约定一致）
                                            list_found = None
                                            for key in ("movies", "tv_shows", "items"):
                                                if key in parsed_data and isinstance(parsed_data[key], list):
                                                    list_found = parsed_data[key]
                                                    break
                                            if list_found is not None:
                                                parsed_data = list_found
                                            # 格式2: {"1": {"中文名": ...}, "2": {...}, ...}（兼容旧格式）
                                            elif parsed_data and all(
                                                str(k).isdigit() for k in parsed_data.keys()
                                            ) and isinstance(next(iter(parsed_data.values()), None), dict):
                                                keys_sorted = sorted(parsed_data.keys(), key=lambda x: int(x))
                                                parsed_data = [parsed_data[k] for k in keys_sorted]
                                            else:
                                                parsed_data = [parsed_data]
                                        elif not isinstance(parsed_data, list):
                                            logging.error(f"解析的数据不是字典或列表: {parsed_data}")
                                            return []

                                        # 转换键名为英文
                                        results = []
                                        for item in parsed_data:
                                            if isinstance(item, dict):
                                                # 尝试不同的键名
                                                chinese_title = (
                                                    item.get('中文名', '')
                                                    or item.get('中文标题', '')
                                                    or item.get('chinese_title', '')
                                                    or item.get('chinese_name', '')
                                                    or item.get('title_cn', '')
                                                    or item.get('name_cn', '')
                                                    or item.get('chinese', '')
                                                )
                                                english_title = (
                                                    item.get('英文名', '')
                                                    or item.get('英文标题', '')
                                                    or item.get('english_title', '')
                                                    or item.get('english_name', '')
                                                    or item.get('title_en', '')
                                                    or item.get('name_en', '')
                                                    or item.get('english', '')
                                                )
                                                year = (
                                                    item.get('年份', '')
                                                    or item.get('上映年份', '')
                                                    or item.get('year', '')
                                                )
                                                
                                                results.append({
                                                    'chinese_title': chinese_title,
                                                    'english_title': english_title,
                                                    'year': year
                                                })
                                            else:
                                                logging.error(f"无效的数据项: {item}")
                                        
                                        return results
                                    except Exception as e:
                                        logging.error(f"JSON解析错误: {str(e)}, 清理后的内容: {json_str}")
                                        # 尝试提取每个文件的信息
                                        results = []
                                        for filename in filenames:
                                            # 在内容中查找文件名相关的信息
                                            filename_start = content.find(filename)
                                            if filename_start != -1:
                                                # 提取文件名后的内容直到下一个文件名或结束
                                                next_filename_start = content.find('\n', filename_start)
                                                if next_filename_start == -1:
                                                    next_filename_start = len(content)
                                                info_text = content[filename_start:next_filename_start]
                                                
                                                # 尝试提取信息
                                                chinese_title = ""
                                                english_title = ""
                                                year = ""
                                                
                                                # 查找中文名
                                                cn_idx = info_text.find('中文名')
                                                if cn_idx != -1:
                                                    cn_end = info_text.find('\n', cn_idx)
                                                    if cn_end == -1:
                                                        cn_end = len(info_text)
                                                    chinese_title = info_text[cn_idx+2:cn_end].strip()
                                                
                                                # 查找英文名
                                                en_idx = info_text.find('英文名')
                                                if en_idx != -1:
                                                    en_end = info_text.find('\n', en_idx)
                                                    if en_end == -1:
                                                        en_end = len(info_text)
                                                    english_title = info_text[en_idx+2:en_end].strip()
                                                
                                                # 查找年份
                                                year_idx = info_text.find('年份')
                                                if year_idx != -1:
                                                    year_end = info_text.find('\n', year_idx)
                                                    if year_end == -1:
                                                        year_end = len(info_text)
                                                    year = info_text[year_idx+2:year_end].strip()
                                                
                                                results.append({
                                                    'chinese_title': chinese_title,
                                                    'english_title': english_title,
                                                    'year': year
                                                })
                                        
                                        if results:
                                            return results
                                        return []
                                else:
                                    logging.error("无法从API响应中提取JSON数据")
                                    return []
                            except Exception as e:
                                logging.error(f"解析API响应失败: {str(e)}")
                                return []
                    except asyncio.TimeoutError:
                        logging.error(f"Grok API请求超时，重试 ({retry_count+1}/{max_retries})")
                        retry_count += 1
                        await asyncio.sleep(1)
                    except Exception as e:
                        logging.error(f"Grok API请求失败: {str(e)}, 重试 ({retry_count+1}/{max_retries})")
                        self.stats.add_error()
                        retry_count += 1
                        await asyncio.sleep(1)
                    else:
                        break  # 如果成功，退出循环
                        
                # 如果重试耗尽仍然失败
                if retry_count >= max_retries:
                    logging.error(f"Grok API请求达到最大重试次数 ({max_retries})，放弃")
                    return []
        except Exception as e:
            logging.error(f"Grok API调用失败: {str(e)}")
            self.stats.add_error()
            return []

    async def parse_filenames(self, filenames: List[str]) -> List[Dict]:
        """Parse multiple filenames using Grok API with concurrency control."""
        # 重新获取最新配置的batch_size
        from ..core.config import config_manager
        current_settings = config_manager.settings
        # 按照批处理大小将文件名分组
        batch_size = current_settings.grok_batch_size
        batches = [filenames[i:i + batch_size] for i in range(0, len(filenames), batch_size)]
        logging.info(f"将 {len(filenames)} 个文件分成 {len(batches)} 个批次，每批 {batch_size} 个文件")
        
        # 创建一个用于处理单个批次的函数
        async def process_batch(batch):
            return await self.parse_single_filename_batch(batch)
        
        # 创建所有批次的任务
        tasks = []
        for batch in batches:
            # 使用速率限制器确保不超过API限制
            tasks.append(process_batch(batch))
        
        # 串行执行所有批次
        results = []
        for task in tasks:
            batch_result = await task
            results.extend(batch_result)
        
        return results[:len(filenames)]  # 确保返回结果数量与文件名数量一致

class TMDBAPI:
    def __init__(self):
        # 从配置管理器获取最新配置，而不是直接使用settings
        from ..core.config import config_manager
        current_settings = config_manager.settings
        
        self.api_key = current_settings.tmdb_api_key
        self.base_url = "https://api.themoviedb.org/3"
        # 设置代理
        self.proxy = f"http://{current_settings.proxy_url.strip()}" if current_settings.proxy_url else None
        # 设置速率限制器
        self.rate_limiter = RateLimiter(current_settings.tmdb_rate_limit)
        logging.info(f"TMDBAPI 代理设置: {self.proxy}")
        logging.info(f"TMDBAPI 速率限制: {current_settings.tmdb_rate_limit} 请求/秒")
        # 初始化统计对象
        self.stats = APIStats("TMDB")

    async def search_movie(self, title: str, year: Optional[str] = None, language: Optional[str] = None) -> List[Dict]:
        """Search movie on TMDB and return a list of search results."""
        params = {
            "api_key": self.api_key,
            "language": language or "zh-CN",
            "query": title,
            "include_adult": "false"
        }
        
        if year:
            params["year"] = year
        
        try:
            # 等待获取令牌，速率控制
            await self.rate_limiter.wait_for_token()
            
            # 开始计时
            start_time = time.time()
            
            # 使用更宽松的 SSL 设置
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    async with session.get(
                        f"{self.base_url}/search/movie",
                        params=params,
                        proxy=self.proxy,
                        timeout=30
                    ) as response:
                        # 处理速率限制
                        if response.status == 429:
                            error_text = await response.text()
                            logging.error(f"TMDB API 速率限制错误(429): {error_text}.")
                            self.stats.add_error(is_rate_limit=True)
                            return []
                        
                        if response.status != 200:
                            error_text = await response.text()
                            logging.error(f"TMDB API 搜索电影错误响应: {error_text}")
                            self.stats.add_error()
                            return []
                        
                        response.raise_for_status()
                        result = await response.json()
                        
                        # 结束计时并记录统计信息
                        end_time = time.time()
                        self.stats.add_call(end_time - start_time)
                        
                        # 解析API返回的内容
                        try:
                            if result.get("results"):
                                # 返回所有结果，而不仅仅是第一个
                                movies = []
                                for movie in result["results"][:10]:  # 限制返回前10个结果
                                    # 从release_date中提取年份，确保格式正确（四位数字）
                                    release_date = movie.get("release_date", "")
                                    year = ""
                                    if release_date and len(release_date) >= 4:
                                        year_str = release_date[:4]
                                        # 确保年份是四位数字
                                        if year_str.isdigit() and len(year_str) == 4:
                                            year = year_str
                                    
                                    movies.append({
                                        "id": str(movie["id"]),
                                        "title": movie.get("title", ""),
                                        "original_title": movie.get("original_title", ""),
                                        "release_date": release_date,
                                        "year": year,
                                        "overview": movie.get("overview", ""),
                                        "poster_path": movie.get("poster_path", ""),
                                        "vote_average": movie.get("vote_average", 0),
                                        "popularity": movie.get("popularity", 0)
                                    })
                                logging.info(f"找到 {len(movies)} 个匹配的电影")
                                return movies
                            else:
                                logging.info("没有找到匹配的电影")
                                return []
                        except Exception as e:
                            logging.error(f"解析API响应失败: {str(e)}")
                            return []
                except asyncio.TimeoutError:
                    logging.error(f"TMDB API请求超时")
                    self.stats.add_error()
                    return []
                except Exception as e:
                    logging.error(f"TMDB API请求失败: {str(e)}")
                    self.stats.add_error()
                    return []
        except Exception as e:
            logging.error(f"TMDB API调用失败: {str(e)}")
            self.stats.add_error()
            return []

    async def get_movie_details(self, movie_id: int) -> Dict:
        """Get detailed information about a movie."""
        params = {
            "api_key": self.api_key,
            "language": "zh-CN"
        }

        try:
            # 等待获取令牌，速率控制
            await self.rate_limiter.wait_for_token()
            
            # 开始计时
            start_time = time.time()
            
            # 使用更宽松的 SSL 设置
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    async with session.get(
                        f"{self.base_url}/movie/{movie_id}",
                        params=params,
                        proxy=self.proxy,
                        timeout=30
                    ) as response:
                        # 处理速率限制
                        if response.status == 429:
                            error_text = await response.text()
                            logging.error(f"TMDB API 速率限制错误(429): {error_text}.")
                            self.stats.add_error(is_rate_limit=True)
                            return {}
                        
                        if response.status != 200:
                            error_text = await response.text()
                            logging.error(f"TMDB API 获取电影详情错误响应: {error_text}")
                            self.stats.add_error()
                            return {}
                        
                        response.raise_for_status()
                        result = await response.json()
                        
                        # 结束计时并记录统计信息
                        end_time = time.time()
                        self.stats.add_call(end_time - start_time)
                        
                        return result
                except asyncio.TimeoutError:
                    logging.error(f"TMDB API请求超时")
                    self.stats.add_error()
                    return {}
                except Exception as e:
                    logging.error(f"TMDB API请求失败: {str(e)}")
                    self.stats.add_error()
                    return {}
        except Exception as e:
            logging.error(f"获取TMDB电影详情失败: {str(e)}")
            self.stats.add_error()
            return {}

    async def get_movie_alternative_titles(self, movie_id: int) -> Dict:
        """Get alternative titles for a movie (TMDB API: /movie/{id}/alternative_titles)."""
        params = {"api_key": self.api_key}
        try:
            await self.rate_limiter.wait_for_token()
            start_time = time.time()
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    async with session.get(
                        f"{self.base_url}/movie/{movie_id}/alternative_titles",
                        params=params,
                        proxy=self.proxy,
                        timeout=30
                    ) as response:
                        if response.status != 200:
                            return {}
                        result = await response.json()
                        end_time = time.time()
                        self.stats.add_call(end_time - start_time)
                        return result
                except Exception as e:
                    logging.debug(f"get_movie_alternative_titles failed: {e}")
                    return {}
        except Exception as e:
            logging.debug(f"get_movie_alternative_titles failed: {e}")
            return {}

    async def get_movie_translations(self, movie_id: int) -> Dict:
        """Get translations for a movie (TMDB API: /movie/{id}/translations)."""
        params = {"api_key": self.api_key}
        try:
            await self.rate_limiter.wait_for_token()
            start_time = time.time()
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    async with session.get(
                        f"{self.base_url}/movie/{movie_id}/translations",
                        params=params,
                        proxy=self.proxy,
                        timeout=30
                    ) as response:
                        if response.status != 200:
                            return {}
                        result = await response.json()
                        end_time = time.time()
                        self.stats.add_call(end_time - start_time)
                        return result
                except Exception as e:
                    logging.debug(f"get_movie_translations failed: {e}")
                    return {}
        except Exception as e:
            logging.debug(f"get_movie_translations failed: {e}")
            return {}

    @staticmethod
    def is_chinese(word: str) -> bool:
        """Check if text contains Chinese characters (refer to aigua.tv logic)."""
        if not word:
            return False
        if isinstance(word, list):
            word = " ".join(word)
        return bool(re.search(r'[\u4e00-\u9fff]', word))

    def _get_chinese_name_from_movie_alternative_titles(self, tmdb_info: Dict) -> Optional[str]:
        """Get Chinese name from movie alternative_titles with iso_3166_1 = 'CN' (refer to aigua.tv)."""
        # Movie API: alternative_titles.titles[] with .iso_3166_1, .title
        titles = tmdb_info.get("alternative_titles", {}).get("titles", [])
        for alt in titles:
            if alt.get("iso_3166_1") == "CN" and alt.get("title"):
                logging.debug(f"  Found Chinese name from movie alternative_titles: '{alt['title']}' (iso_3166_1=CN)")
                return alt["title"]
        return None

    def _get_chinese_name_from_movie_translations(self, tmdb_info: Dict) -> Optional[str]:
        """Get Chinese name from movie translations with iso_3166_1 = 'CN' (refer to aigua.tv)."""
        # Movie API: translations.translations[] with .iso_3166_1, .data.title
        translations = tmdb_info.get("translations", {}).get("translations", [])
        for t in translations:
            if t.get("iso_3166_1") == "CN":
                name = t.get("data", {}).get("title")
                if name:
                    logging.debug(f"  Found Chinese name from movie translations: '{name}' (iso_3166_1=CN)")
                    return name
        # Fallback: zh language
        for t in translations:
            if t.get("iso_639_1") == "zh":
                name = t.get("data", {}).get("title")
                if name:
                    logging.debug(f"  Found Chinese name from movie translations: '{name}' (iso_639_1=zh)")
                    return name
        return None

    async def get_chinese_title_for_movie(self, current_title: str, movie_id: int) -> str:
        """
        If current_title contains Chinese, return it. Otherwise fetch alternative_titles and
        translations and return Chinese name for CN (refer to aigua.tv _ensure_chinese_name).
        """
        if not current_title:
            return current_title
        if self.is_chinese(current_title):
            logging.debug(f"  Title '{current_title}' already contains Chinese, no need to replace")
            return current_title
        logging.info(f"  Title '{current_title}' has no Chinese, fetching alternative_titles/translations for Chinese name...")
        try:
            alt = await self.get_movie_alternative_titles(movie_id)
            await asyncio.sleep(0.05)
            trans = await self.get_movie_translations(movie_id)
            tmdb_info = {"alternative_titles": alt, "translations": trans}
            chinese_name = self._get_chinese_name_from_movie_alternative_titles(tmdb_info)
            if not chinese_name:
                chinese_name = self._get_chinese_name_from_movie_translations(tmdb_info)
            if chinese_name:
                logging.info(f"  → Using Chinese name from TMDB: '{chinese_name}'")
                return chinese_name
            logging.warning("  → No Chinese name found in alternative_titles or translations, keeping original title")
        except Exception as e:
            logging.warning(f"  → Failed to get Chinese name: {e}, keeping original title")
        return current_title

    # 新增方法：根据ID获取电影
    async def get_movie_by_id(self, movie_id: int) -> Optional[Dict]:
        """Get movie by TMDB ID and return the movie data."""
        try:
            details = await self.get_movie_details(movie_id)
            if details:
                # 从release_date中提取年份，确保格式正确（四位数字）
                release_date = details.get("release_date", "")
                year = ""
                if release_date and len(release_date) >= 4:
                    year_str = release_date[:4]
                    # 确保年份是四位数字
                    if year_str.isdigit() and len(year_str) == 4:
                        year = year_str
                
                return {
                    "id": str(details.get("id")),
                    "title": details.get("title", ""),
                    "original_title": details.get("original_title", ""),
                    "release_date": release_date,
                    "year": year,
                    "overview": details.get("overview", ""),
                    "poster_path": details.get("poster_path", ""),
                    "vote_average": details.get("vote_average", 0),
                    "popularity": details.get("popularity", 0)
                }
            return None
        except Exception as e:
            logging.error(f"获取电影失败: {str(e)}")
            self.stats.add_error()
            return None

    async def find_by_external_id(self, external_id: str, external_source: str = "imdb_id") -> Optional[Dict]:
        """Find movie by external ID (IMDB, TVDB, etc.) using TMDB's Find API.
        
        Args:
            external_id: The ID from the external source (e.g., IMDB ID starting with 'tt')
            external_source: The external source type (default: imdb_id)
        
        Returns:
            Dictionary containing the movie information if found, None otherwise
        """
        params = {
            "api_key": self.api_key,
            "language": "zh-CN",  # 确保设置语言为中文
            "external_source": external_source
        }

        logging.info(f"使用 TMDB Find API 查找外部ID: {external_id}, 外部源: {external_source}")
        print(f"使用 TMDB Find API 查找外部ID: {external_id}, 外部源: {external_source}")
        print(f"TMDB API Key: {self.api_key[:4]}...{self.api_key[-4:]}")  # 打印部分API Key用于调试

        try:
            # 等待获取令牌，速率控制
            await self.rate_limiter.wait_for_token()
            
            # 开始计时
            start_time = time.time()
            
            # 使用更宽松的 SSL 设置
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    # 构建完整URL和参数
                    url = f"{self.base_url}/find/{external_id}"
                    full_params_str = "&".join([f"{k}={v}" for k, v in params.items()])
                    full_url = f"{url}?{full_params_str}"
                    
                    logging.info(f"TMDB API 请求URL: {url}")
                    print(f"TMDB API 完整请求URL: {full_url}")
                    print(f"TMDB API 参数: {params}")
                    print(f"TMDB API 代理: {self.proxy}")
                    
                    async with session.get(
                        url,
                        params=params,
                        proxy=self.proxy,
                        timeout=30
                    ) as response:
                        response_status = response.status
                        response_text = await response.text()
                        
                        print(f"TMDB API 响应状态码: {response_status}")
                        print(f"TMDB API 响应内容: {response_text}")
                        
                        # 处理速率限制
                        if response_status == 429:
                            logging.error(f"TMDB API 速率限制错误(429): {response_text}.")
                            print(f"TMDB API 速率限制错误(429): {response_text}.")
                            self.stats.add_error(is_rate_limit=True)
                            return None
                        
                        if response_status != 200:
                            logging.error(f"TMDB API 通过外部ID查找电影失败: 状态码={response_status}, 错误={response_text}")
                            print(f"TMDB API 通过外部ID查找电影失败: 状态码={response_status}, 错误={response_text}")
                            self.stats.add_error()
                            return None
                        
                        response.raise_for_status()
                        
                        # 解析JSON响应
                        try:
                            result = json.loads(response_text)
                        except json.JSONDecodeError as e:
                            print(f"JSON解析错误: {str(e)}, 原始响应: {response_text}")
                            return None
                        
                        # 结束计时并记录统计信息
                        end_time = time.time()
                        self.stats.add_call(end_time - start_time)
                        
                        # 详细记录API返回内容
                        logging.info(f"TMDB Find API 返回结果: {result}")
                        print(f"TMDB Find API 返回结果详细信息:")
                        print(f"  - movie_results 长度: {len(result.get('movie_results', []))}")
                        print(f"  - tv_results 长度: {len(result.get('tv_results', []))}")
                        print(f"  - person_results 长度: {len(result.get('person_results', []))}")
                        print(f"  - tv_episode_results 长度: {len(result.get('tv_episode_results', []))}")
                        print(f"  - tv_season_results 长度: {len(result.get('tv_season_results', []))}")
                        
                        # 检查结果并返回第一个匹配的电影
                        if result.get("movie_results") and len(result["movie_results"]) > 0:
                            movie = result["movie_results"][0]
                            logging.info(f"找到匹配的电影: ID={movie.get('id')}, 标题={movie.get('title')}")
                            print(f"找到匹配的电影: ID={movie.get('id')}, 标题={movie.get('title')}")
                            
                            # 获取完整的电影详情
                            if movie.get("id"):
                                movie_details = await self.get_movie_by_id(movie["id"])
                                if movie_details:
                                    logging.info(f"成功获取到电影详情: {movie_details}")
                                    print(f"成功获取到电影详情: {movie_details}")
                                    return movie_details
                                else:
                                    logging.error(f"无法获取电影详情，ID: {movie['id']}")
                                    print(f"无法获取电影详情，ID: {movie['id']}")
                            else:
                                logging.error("找到的电影结果没有ID")
                                print("找到的电影结果没有ID")
                        else:
                            logging.warning(f"未找到与IMDB ID: {external_id} 匹配的电影")
                            print(f"未找到与IMDB ID: {external_id} 匹配的电影")
                            print(f"请检查IMDB ID格式是否正确，示例格式: tt0111161")
                            if external_source != "imdb_id":
                                print(f"注意: 当前使用的外部源类型是 '{external_source}'，而不是 'imdb_id'")
                            
                        return None
                except asyncio.TimeoutError:
                    logging.error(f"TMDB API请求超时: {url}")
                    print(f"TMDB API请求超时: {url}")
                    self.stats.add_error()
                    return None
                except Exception as e:
                    logging.error(f"TMDB API请求失败: {str(e)}")
                    print(f"TMDB API请求失败: {str(e)}")
                    print(f"错误详情: {traceback.format_exc()}")
                    self.stats.add_error()
                    return None
        except Exception as e:
            logging.error(f"通过外部ID查找电影失败: {str(e)}")
            print(f"通过外部ID查找电影失败: {str(e)}")
            print(f"错误堆栈: {traceback.format_exc()}")
            self.stats.add_error()
            return None

class MediaInfoService:
    def __init__(self):
        # 确保获取最新配置
        from ..core.config import config_manager
        current_settings = config_manager.settings
        logging.info(f"初始化 MediaInfoService 使用以下配置: grok_rate_limit={current_settings.grok_rate_limit}, tmdb_rate_limit={current_settings.tmdb_rate_limit}")
        
        self.grok_api = GrokAPI()
        self.tmdb_api = TMDBAPI()
        
        # 直接使用TMDB API的速率限制
        logging.info(f"TMDB API 速率限制: {current_settings.tmdb_rate_limit} 请求/秒")

    def generate_new_filename(self, chinese_title: str, english_title: str, year: str, tmdb_id: str = None) -> str:
        """生成新的文件名"""
        # 如果没有 TMDB ID，直接返回空字符串
        if not tmdb_id:
            return ""
            
        # 如果没有任何标题，返回空字符串
        if not chinese_title and not english_title:
            return ""
        
        # 优先使用中文标题，如果没有则使用英文标题
        title = chinese_title if chinese_title else english_title
        
        # 如果year是None、空字符串、'undefined'、'null'或'未知'，视为无效年份
        if not year or year in ['undefined', 'null', '未知']:
            # 如果没有有效年份，不生成文件名
            return ""
        
        # 如果有年份，添加到标题后面
        title = f"{title} ({year})"
        
        # 添加 TMDB ID 到标题后面
        title = f"{title} {{tmdb-{tmdb_id}}}"
        
        # 移除非法路径字符（如 / * 等）
        from ..utils.file_utils import sanitize_path_component
        return sanitize_path_component(title)

    def _pick_best_movie_by_year(self, tmdb_movies: List[Dict], requested_year: str) -> Optional[Dict]:
        """从 TMDB 搜索结果中优先选择年份与解析结果一致的电影，避免误匹配（如 重生 2004 vs 富江：重生 2001）。"""
        if not tmdb_movies:
            return None
        requested_year_str = str(requested_year).strip() if requested_year else ""
        if not requested_year_str:
            return tmdb_movies[0]
        for m in tmdb_movies:
            y = m.get("year") or ""
            if not y and m.get("release_date"):
                y = str(m["release_date"])[:4]
            if str(y).strip() == requested_year_str:
                return m
        return tmdb_movies[0]

    async def process_filenames(self, filenames: List[str]) -> List[Dict]:
        """Process multiple filenames to extract media information."""
        try:
            print(f"开始处理文件名列表：{filenames}")  # 添加日志
            # 使用 Grok AI 解析文件名
            grok_results = await self.grok_api.parse_filenames(filenames)
            print(f"Grok API 返回结果：{grok_results}")  # 添加日志
            
            # 处理完成后，输出API统计信息
            self.grok_api.stats.print_stats()
            
            # 处理每个结果
            results = []
            
            async def process_single_file(filename: str, grok_result: Dict) -> Dict:
                try:
                    print(f"处理文件：{filename}")  # 添加日志
                    # 从 Grok 结果中提取信息
                    chinese_title = grok_result.get("chinese_title", "")
                    english_title = grok_result.get("english_title", "")
                    year = grok_result.get("year", "")
                    print(f"Grok 解析结果：中文名={chinese_title}, 英文名={english_title}, 年份={year}")  # 添加日志
                    
                    # 尝试在 TMDB 上查找电影
                    tmdb_movies = []
                    language = None
                    if chinese_title and year:
                        print(f"使用中文名搜索 TMDB：{chinese_title} ({year})")  # 添加日志
                        tmdb_movies = await self.tmdb_api.search_movie(chinese_title, year, language)
                    elif english_title and year:
                        print(f"使用英文名搜索 TMDB：{english_title} ({year})")  # 添加日志
                        tmdb_movies = await self.tmdb_api.search_movie(english_title, year, language)
                    
                    # 获取 TMDB ID（优先选择年份与解析结果一致的电影，避免误匹配）
                    tmdb_id = None
                    if tmdb_movies and len(tmdb_movies) > 0:
                        first_movie = self._pick_best_movie_by_year(tmdb_movies, year)
                        if not first_movie:
                            first_movie = tmdb_movies[0]
                        tmdb_id_str = first_movie["id"]
                        print(f"找到 TMDB ID（字符串）：{tmdb_id_str}")  # 添加日志
                        
                        # 转换字符串ID为整数，用于验证
                        try:
                            tmdb_id_int = int(tmdb_id_str)
                        except (ValueError, TypeError) as e:
                            print(f"警告: 无法将TMDB ID转换为整数: {tmdb_id_str}, 错误: {e}")
                            tmdb_id = None
                        else:
                            # 验证ID是否存在 - 调用get_movie_details验证
                            details = await self.tmdb_api.get_movie_details(tmdb_id_int)
                            
                            # 检查是否返回有效数据（非空字典且包含id字段）
                            if details and isinstance(details, dict) and details.get("id"):
                                # ID验证成功，使用字符串ID
                                tmdb_id = tmdb_id_str
                                print(f"TMDB ID验证成功：{tmdb_id}")  # 添加日志
                                
                                # 如果有官方中文标题，使用它
                                if details.get("title"):
                                    chinese_title = details["title"]
                                    print(f"使用 TMDB 官方中文标题：{chinese_title}")  # 添加日志
                                
                                # 若目标文件名不含中文，则从 TMDB 的 alternative_titles/translations 取中文名（参考 aigua.tv）
                                title_for_filename = chinese_title if chinese_title else english_title
                                if title_for_filename and tmdb_id and not self.tmdb_api.is_chinese(title_for_filename):
                                    chinese_title = await self.tmdb_api.get_chinese_title_for_movie(title_for_filename, tmdb_id_int)
                                    if chinese_title != title_for_filename:
                                        print(f"使用 TMDB 中文名作为文件名标题：{chinese_title}")
                            else:
                                # ID验证失败，不存储无效ID
                                print(f"警告: TMDB ID {tmdb_id_int} 验证失败，返回的数据无效或为空")
                                logging.warning(f"TMDB ID {tmdb_id_int} 验证失败，返回的数据无效或为空")
                                tmdb_id = None
                    
                    # 生成新的文件名
                    new_name = self.generate_new_filename(chinese_title, english_title, year, tmdb_id)
                    print(f"生成的新文件名：{new_name}")  # 添加日志
                    
                    result = {
                        "path": filename,
                        "original_path": filename,
                        "chinese_title": chinese_title,
                        "english_title": english_title,
                        "year": year,
                        "tmdb_id": str(tmdb_id) if tmdb_id is not None else None,
                        "new_name": new_name
                    }
                    print(f"最终结果：{result}")  # 添加日志
                    return result
                    
                except Exception as e:
                    print(f"处理文件 {filename} 时出错：{str(e)}")  # 添加错误日志
                    return {
                        "path": filename,
                        "original_path": filename,
                        "error": str(e),
                        "chinese_title": "",
                        "english_title": "",
                        "year": "",
                        "tmdb_id": None,
                        "new_name": ""
                    }
            
            # 创建所有文件处理任务
            tasks = []
            for filename, grok_result in zip(filenames, grok_results):
                tasks.append(process_single_file(filename, grok_result))
            
            # 并发执行所有文件处理任务
            results = await asyncio.gather(*tasks)
            
            # 在处理完所有文件后输出TMDB API统计信息
            self.tmdb_api.stats.print_stats()
            
            print(f"所有文件处理完成，结果：{results}")  # 添加日志
            return results
            
        except Exception as e:
            print(f"批量处理文件名时出错：{str(e)}")  # 添加错误日志
            # 即使发生错误，也输出统计信息
            self.grok_api.stats.print_stats()
            self.tmdb_api.stats.print_stats()
            return [{
                "original_path": filename,
                "error": str(e),
                "chinese_title": "",
                "english_title": "",
                "year": "",
                "tmdb_id": None,
                "new_name": ""
            } for filename in filenames]

    # 新版并行执行Grok和TMDB查询（优化批处理）
    async def process_filenames_parallel(self, filenames: List[str], file_media_types: dict = None, print_stats: bool = True) -> List[Dict]:
        """Process multiple filenames with parallel Grok and TMDB operations.
        
        Args:
            filenames: 要处理的文件名列表
            file_media_types: 文件路径到媒体类型（movie/tv）的映射字典
            print_stats: 是否在方法内部打印统计信息，默认为True
        """
        try:
            print(f"开始并行处理文件名列表：{filenames}")
            
            # 获取最新配置
            from ..core.config import config_manager
            current_settings = config_manager.settings
            print(f"并行处理使用以下配置: grok_rate_limit={current_settings.grok_rate_limit}, tmdb_rate_limit={current_settings.tmdb_rate_limit}, grok_batch_size={current_settings.grok_batch_size}")
            
            # 如果没有提供文件媒体类型映射，创建一个默认的（全部为电影）
            if file_media_types is None:
                file_media_types = {filename: "movie" for filename in filenames}
            
            # 保存最终结果的字典，使用索引作为KEY保证顺序
            results_dict = {}
            
            # 待处理的TMDB任务队列
            tmdb_queue = asyncio.Queue()
            
            # 消费TMDB队列的任务
            async def tmdb_worker():
                while True:
                    try:
                        # 从队列获取任务
                        index, filename, grok_result = await tmdb_queue.get()
                        
                        try:
                            # 处理TMDB查询部分
                            result = await self._process_tmdb_info(filename, grok_result)
                            # 保存结果，使用索引确保最终顺序与输入一致
                            results_dict[index] = result
                        except Exception as e:
                            print(f"处理TMDB信息时出错：{str(e)}")
                            results_dict[index] = {
                                "path": filename,
                                "original_path": filename,
                                "chinese_title": grok_result.get("chinese_title", ""),
                                "english_title": grok_result.get("english_title", ""),
                                "year": grok_result.get("year", ""),
                                "tmdb_id": None,
                                "new_name": ""
                            }
                        finally:
                            # 标记任务完成
                            tmdb_queue.task_done()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"TMDB工作线程出错：{str(e)}")
            
            # 启动TMDB工作线程 - 使用速率限制，最多启动与速率相同数量的工作线程
            worker_count = min(50, current_settings.tmdb_rate_limit)  # 确保最多50个工作线程
            print(f"启动 {worker_count} 个TMDB工作线程")
            tmdb_tasks = [asyncio.create_task(tmdb_worker()) for _ in range(worker_count)]
            
            # 按照批处理大小将文件名分组
            batch_size = current_settings.grok_batch_size
            batches = [filenames[i:i + batch_size] for i in range(0, len(filenames), batch_size)]
            print(f"将 {len(filenames)} 个文件分成 {len(batches)} 个批次，每批 {batch_size} 个文件")
            
            # 处理单个批次的Grok部分
            async def process_grok_batch(batch_index, batch_filenames):
                try:
                    # 使用Grok API的批处理能力
                    batch_start_indices = [filenames.index(fname) for fname in batch_filenames]
                    print(f"处理批次 {batch_index+1}/{len(batches)}，文件数量: {len(batch_filenames)}")
                    
                    # 获取此批次文件的媒体类型
                    batch_media_types = {fname: file_media_types.get(fname, "movie") for fname in batch_filenames}
                    
                    # 使用Grok批处理API，传递媒体类型
                    grok_results = await self.grok_api.parse_single_filename_batch(batch_filenames, batch_media_types)
                    
                    # 确保结果数量与批次文件数量一致
                    if grok_results and len(grok_results) > 0:
                        # 将每个Grok结果立即放入TMDB队列处理
                        for i, (fname, result) in enumerate(zip(batch_filenames, grok_results)):
                            original_index = batch_start_indices[i]
                            if result:
                                await tmdb_queue.put((original_index, fname, result))
                            else:
                                # Grok解析失败 - 不添加错误信息，保持新文件名为空
                                results_dict[original_index] = {
                                    "path": fname,
                                    "original_path": fname,
                                    "chinese_title": "",
                                    "english_title": "",
                                    "year": "",
                                    "tmdb_id": None,
                                    "new_name": ""
                                }
                    else:
                        # 整个批次处理失败 - 不添加错误信息，保持新文件名为空
                        for i, fname in enumerate(batch_filenames):
                            original_index = batch_start_indices[i]
                            results_dict[original_index] = {
                                "path": fname,
                                "original_path": fname,
                                "chinese_title": "",
                                "english_title": "",
                                "year": "",
                                "tmdb_id": None,
                                "new_name": ""
                            }
                except Exception as e:
                    print(f"Grok批处理出错: {str(e)}")
                    # 为批次中的所有文件设置空结果，不添加错误信息
                    for i, fname in enumerate(batch_filenames):
                        original_index = filenames.index(fname)
                        results_dict[original_index] = {
                            "path": fname,
                            "original_path": fname,
                            "chinese_title": "",
                            "english_title": "",
                            "year": "",
                            "tmdb_id": None,
                            "new_name": ""
                        }
            
            # 创建并执行Grok批处理任务
            grok_tasks = []
            for i, batch in enumerate(batches):
                # 每个批次任务都是独立的，会通过RateLimiter进行速率控制
                grok_tasks.append(process_grok_batch(i, batch))
            
            # 等待所有Grok任务完成
            await asyncio.gather(*grok_tasks)
            
            # 等待所有TMDB任务完成
            await tmdb_queue.join()
            
            # 取消TMDB工作线程
            for task in tmdb_tasks:
                task.cancel()
            
            # 等待工作线程完成取消
            await asyncio.gather(*tmdb_tasks, return_exceptions=True)
            
            # 按原始顺序整理结果
            ordered_results = [results_dict.get(i, {
                "path": filenames[i],
                "original_path": filenames[i],
                "chinese_title": "",
                "english_title": "",
                "year": "",
                "tmdb_id": None,
                "new_name": ""
            }) for i in range(len(filenames))]
            
            # 根据参数决定是否输出统计信息
            if print_stats:
                self.grok_api.stats.print_stats()
                self.tmdb_api.stats.print_stats()
            
            return ordered_results
            
        except Exception as e:
            print(f"并行处理文件名时出错：{str(e)}")
            # 根据参数决定是否输出统计信息
            if print_stats:
                # 即使发生错误，也输出统计信息
                self.grok_api.stats.print_stats()
                self.tmdb_api.stats.print_stats()
            return [{
                "original_path": filename,
                "chinese_title": "",
                "english_title": "",
                "year": "",
                "tmdb_id": None,
                "new_name": ""
            } for filename in filenames]
            
    async def _process_tmdb_info(self, filename: str, grok_result: Dict) -> Dict:
        """处理单个文件的TMDB信息查询"""
        try:
            # 从 Grok 结果中提取信息
            chinese_title = grok_result.get("chinese_title", "")
            english_title = grok_result.get("english_title", "")
            year = grok_result.get("year", "")
            print(f"Grok 解析结果：中文名={chinese_title}, 英文名={english_title}, 年份={year}")
            
            # 尝试在 TMDB 上查找电影
            tmdb_movies = []
            
            # 优先使用中文名搜索，如果有年份则加上年份
            if chinese_title:
                print(f"使用中文名搜索 TMDB：{chinese_title}" + (f" ({year})" if year else ""))
            tmdb_movies = await self.tmdb_api.search_movie(chinese_title, year if year else None)
            
            # 如果没有结果，尝试英文名搜索
            if (not tmdb_movies or len(tmdb_movies) == 0) and english_title:
                print(f"使用英文名搜索 TMDB：{english_title}" + (f" ({year})" if year else ""))
                tmdb_movies = await self.tmdb_api.search_movie(english_title, year if year else None)
            
            # 获取 TMDB ID和标题（优先选择年份与解析结果一致的电影，避免误匹配）
            tmdb_id = None
            new_name = ""  # 默认为空字符串
            if tmdb_movies and len(tmdb_movies) > 0:
                first_movie = self._pick_best_movie_by_year(tmdb_movies, year)
                if not first_movie:
                    first_movie = tmdb_movies[0]
                tmdb_id_str = first_movie["id"]
                
                # 转换字符串ID为整数，用于验证
                try:
                    tmdb_id_int = int(tmdb_id_str)
                except (ValueError, TypeError) as e:
                    print(f"警告: 无法将TMDB ID转换为整数: {tmdb_id_str}, 错误: {e}")
                    tmdb_id = None
                else:
                    # 验证ID是否存在 - 调用get_movie_details验证
                    details = await self.tmdb_api.get_movie_details(tmdb_id_int)
                    
                    # 检查是否返回有效数据（非空字典）
                    if details and isinstance(details, dict) and details.get("id"):
                        # ID验证成功，使用字符串ID（保持与API返回格式一致）
                        tmdb_id = tmdb_id_str
                        
                        # 检查search返回的结果是否已经包含中文标题
                        # search_movie方法在搜索时已经指定language=zh-CN
                        # 如果搜索结果中已有中文标题，直接使用，避免额外的API调用
                        if first_movie.get("title"):
                            chinese_title = first_movie["title"]
                            print(f"从搜索结果使用TMDB中文标题：{chinese_title}")
                        elif details.get("title"):
                            # 如果search结果中没有中文标题，使用详情中的标题
                            chinese_title = details["title"]
                            print(f"从详情使用TMDB官方中文标题：{chinese_title}")
                        
                        # 使用TMDB返回的年份（如果有）
                        if first_movie.get("year"):
                            year = first_movie["year"]
                            print(f"使用TMDB返回的年份：{year}")
                        elif details.get("release_date"):
                            # 从详情中提取年份
                            release_date = details.get("release_date", "")
                            if release_date and len(release_date) >= 4:
                                year_str = release_date[:4]
                                if year_str.isdigit() and len(year_str) == 4:
                                    year = year_str
                                    print(f"从详情使用TMDB返回的年份：{year}")
                        
                        # 若目标文件名不含中文，则从 TMDB 的 alternative_titles/translations 取中文名（参考 aigua.tv）
                        title_for_filename = chinese_title if chinese_title else english_title
                        if title_for_filename and not self.tmdb_api.is_chinese(title_for_filename):
                            chinese_title = await self.tmdb_api.get_chinese_title_for_movie(title_for_filename, tmdb_id_int)
                            if chinese_title != title_for_filename:
                                print(f"使用 TMDB 中文名作为文件名标题：{chinese_title}")
                        
                        # 只有在成功验证TMDB ID的情况下才生成新文件名
                        new_name = self.generate_new_filename(chinese_title, english_title, year, tmdb_id)
                        print(f"生成的新文件名：{new_name}")
                    else:
                        # ID验证失败，不存储无效ID
                        print(f"警告: TMDB ID {tmdb_id_int} 验证失败，返回的数据无效或为空")
                        logging.warning(f"TMDB ID {tmdb_id_int} 验证失败，返回的数据无效或为空")
                        tmdb_id = None
            
            return {
                "path": filename,
                "original_path": filename,
                "chinese_title": chinese_title,
                "english_title": english_title,
                "year": year,
                "tmdb_id": str(tmdb_id) if tmdb_id is not None else None,
                "new_name": new_name
            }
        except Exception as e:
            print(f"处理TMDB信息时出错：{str(e)}")
            return {
                "path": filename,
                "original_path": filename,
                "chinese_title": "",
                "english_title": "",
                "year": "",
                "tmdb_id": None,
                "new_name": ""
            } 