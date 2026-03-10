from typing import List, Dict, Optional
import os
import re
from datetime import datetime
from ..models.media.tv_models import TVShow, TVSeason, TVEpisode
from ..core.config import ConfigManager
from ..core.tmdb import TMDBClient

class TVShowService:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.media_extensions = config_manager.settings.media_extension.split(';')
        self.subtitle_extensions = config_manager.settings.subtitle_extension.split(';')
        self.tmdb_client = TMDBClient(config_manager)

    async def scan_directory(self, root_path: str) -> TVShow:
        """Scan directory and build TV show structure"""
        show = TVShow(root_path=root_path)
        
        # First, try to identify the show from the root directory name
        show_info = await self._identify_show_from_directory(root_path)
        if show_info:
            show.tmdb_id = str(show_info.get('id'))
            show.title = show_info.get('name')
            show.year = show_info.get('first_air_date', '').split('-')[0]
            show.show_info = show_info
        
        # Scan for season directories
        for item in os.listdir(root_path):
            item_path = os.path.join(root_path, item)
            if os.path.isdir(item_path):
                # Try to identify season number from directory name
                season_number = self._extract_season_number(item)
                if season_number is not None:
                    season = await self._scan_season_directory(season_number, item_path)
                    show.seasons[season_number] = season
        
        return show

    async def _identify_show_from_directory(self, directory_path: str) -> Optional[Dict]:
        """Try to identify TV show from directory name using TMDB"""
        directory_name = os.path.basename(directory_path)
        # Remove common TV show indicators
        clean_name = re.sub(r'\([0-9]{4}\)|\[.*?\]|\(.*?\)', '', directory_name).strip()
        # Search TMDB for the show
        results = await self.tmdb_client.search_tv(clean_name)
        if results and len(results) > 0:
            return results[0]
        return None

    async def _scan_season_directory(self, season_number: int, season_path: str) -> TVSeason:
        """Scan a season directory and identify episodes"""
        season = TVSeason(season_number=season_number, directory_path=season_path)
        
        # Get all files in the directory
        files = os.listdir(season_path)
        
        # Group files by episode number (if they can be identified)
        episode_groups = self._group_files_by_episode(files)
        
        # Create episode objects
        for episode_number, group in episode_groups.items():
            episode = await self._create_episode(season_path, group)
            season.episodes.append(episode)
        
        # Sort episodes by episode number
        season.episodes.sort(key=lambda x: x.episode_info.get('episode_number', 0) if x.episode_info else 0)
        
        return season

    def _group_files_by_episode(self, files: List[str]) -> Dict[int, List[str]]:
        """Group files that belong to the same episode"""
        groups = {}
        for file in files:
            # Try to extract episode number from filename
            episode_number = self._extract_episode_number(file)
            if episode_number is not None:
                if episode_number not in groups:
                    groups[episode_number] = []
                groups[episode_number].append(file)
        return groups

    async def _create_episode(self, season_path: str, files: List[str]) -> TVEpisode:
        """Create an episode object from a group of files"""
        # Find the main media file
        media_file = next(
            (f for f in files if any(f.lower().endswith(ext.lower()) 
                                   for ext in self.media_extensions)),
            None
        )
        
        if not media_file:
            raise ValueError(f"No media file found in group: {files}")
        
        # Find associated subtitle files
        subtitle_files = [
            f for f in files if any(f.lower().endswith(ext.lower()) 
                                  for ext in self.subtitle_extensions)
        ]
        
        file_path = os.path.join(season_path, media_file)
        return TVEpisode(
            file_path=file_path,
            file_name=media_file,
            file_size=os.path.getsize(file_path),
            modified_time=datetime.fromtimestamp(os.path.getmtime(file_path)),
            subtitles=subtitle_files
        )

    async def identify_episodes(self, show: TVShow) -> TVShow:
        """Identify all episodes in a show"""
        if not show.tmdb_id:
            return show

        for season in show.seasons.values():
            # Get season info from TMDB
            season_info = await self._get_season_info(show.tmdb_id, season.season_number)
            season.season_info = season_info
            
            # Identify each episode
            for episode in season.episodes:
                episode_info = await self._identify_episode(
                    show.tmdb_id,
                    season.season_number,
                    episode.file_name
                )
                episode.episode_info = episode_info
        
        return show

    async def _get_season_info(self, show_id: str, season_number: int) -> Optional[Dict]:
        """Get season information from TMDB"""
        try:
            return await self.tmdb_client.get_tv_season(show_id, season_number)
        except Exception as e:
            print(f"Error getting season info: {e}")
            return None

    async def _identify_episode(self, show_id: str, season_number: int, file_name: str) -> Optional[Dict]:
        """Identify episode from filename using TMDB"""
        try:
            # Extract episode number from filename
            episode_number = self._extract_episode_number(file_name)
            if episode_number is None:
                return None
            
            # Get episode info from TMDB
            return await self.tmdb_client.get_tv_episode(show_id, season_number, episode_number)
        except Exception as e:
            print(f"Error identifying episode: {e}")
            return None

    async def rename_show(self, show: TVShow) -> List[Dict]:
        """Rename all episodes in a show following TV show naming convention"""
        results = []
        
        for season in show.seasons.values():
            if not season.selected:
                continue
                
            # Create season directory if needed
            season_dir = os.path.join(
                show.root_path,
                f"Season {season.season_number:02d}"
            )
            os.makedirs(season_dir, exist_ok=True)
            
            # Rename each episode
            for episode in season.episodes:
                if not episode.selected:
                    continue
                    
                # Generate new episode name
                new_name = self._generate_episode_name(
                    show.title,
                    season.season_number,
                    episode.episode_info
                )
                
                # Rename main file
                new_path = os.path.join(season_dir, new_name)
                result = await self._rename_file(episode.file_path, new_path)
                results.append(result)
                
                # Rename subtitle files
                for subtitle in episode.subtitles:
                    subtitle_path = os.path.join(
                        os.path.dirname(episode.file_path),
                        subtitle
                    )
                    new_subtitle = self._generate_subtitle_name(
                        new_name,
                        subtitle
                    )
                    new_subtitle_path = os.path.join(season_dir, new_subtitle)
                    result = await self._rename_file(
                        subtitle_path,
                        new_subtitle_path
                    )
                    results.append(result)
        
        return results

    def _generate_episode_name(
        self,
        show_title: str,
        season_number: int,
        episode_info: Dict
    ) -> str:
        """Generate standardized episode name"""
        episode_number = episode_info.get('episode_number', 0)
        episode_title = episode_info.get('name', '')
        
        return (
            f"{show_title} - S{season_number:02d}E{episode_number:02d}"
            f" - {episode_title}"
        )

    def _generate_subtitle_name(
        self,
        episode_name: str,
        subtitle_file: str
    ) -> str:
        """Generate subtitle name matching episode name"""
        # Extract language code from original subtitle name
        lang_code = self._extract_language_code(subtitle_file)
        # Remove extension from episode name
        base_name = os.path.splitext(episode_name)[0]
        # Get original subtitle extension
        _, ext = os.path.splitext(subtitle_file)
        
        return f"{base_name}.{lang_code}{ext}"

    async def _rename_file(self, old_path: str, new_path: str) -> Dict:
        """Rename a file and return the result"""
        try:
            os.rename(old_path, new_path)
            return {
                "success": True,
                "old_path": old_path,
                "new_path": new_path
            }
        except Exception as e:
            return {
                "success": False,
                "old_path": old_path,
                "new_path": new_path,
                "error": str(e)
            }

    def _extract_season_number(self, directory_name: str) -> Optional[int]:
        """Extract season number from directory name"""
        # Common patterns for season directories
        patterns = [
            r'season\s*(\d+)',  # Season 1, Season1
            r's(\d+)',          # S1
            r'(\d+)$'           # Just the number at the end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, directory_name.lower())
            if match:
                return int(match.group(1))
        return None

    def _extract_episode_number(self, file_name: str) -> Optional[int]:
        """Extract episode number from filename"""
        # Common patterns for episode numbers
        patterns = [
            r'e(\d+)',          # E01
            r'episode\s*(\d+)', # Episode 1
            r'ep(\d+)',         # EP1
            r'(\d+)$'           # Just the number at the end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, file_name.lower())
            if match:
                return int(match.group(1))
        return None

    def _extract_language_code(self, subtitle_file: str) -> str:
        """Extract language code from subtitle filename"""
        # Common patterns for language codes
        patterns = [
            r'\.([a-z]{2,3})\.',  # .en., .eng.
            r'\.([a-z]{2,3})$'    # .en, .eng
        ]
        
        for pattern in patterns:
            match = re.search(pattern, subtitle_file.lower())
            if match:
                return match.group(1)
        return 'eng'  # Default to English if no language code found 