from typing import List, Dict, Optional
import aiohttp

class TMDBClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def search_tv(self, query: str) -> List[Dict]:
        """Search for TV shows"""
        url = f"{self.base_url}/search/tv"
        params = {
            "api_key": self.api_key,
            "query": query,
            "language": "en-US"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("results", [])
                return []

    async def get_tv_show(self, show_id: str) -> Optional[Dict]:
        """Get TV show details"""
        url = f"{self.base_url}/tv/{show_id}"
        params = {
            "api_key": self.api_key,
            "language": "en-US"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return None

    async def get_tv_season(self, show_id: str, season_number: int) -> Optional[Dict]:
        """Get TV season details"""
        url = f"{self.base_url}/tv/{show_id}/season/{season_number}"
        params = {
            "api_key": self.api_key,
            "language": "en-US"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return None

    async def get_tv_episode(self, show_id: str, season_number: int, episode_number: int) -> Optional[Dict]:
        """Get TV episode details"""
        url = f"{self.base_url}/tv/{show_id}/season/{season_number}/episode/{episode_number}"
        params = {
            "api_key": self.api_key,
            "language": "en-US"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return None 