from typing import List, Dict, Optional
import os
import re
from datetime import datetime
from ..models.media.movie_models import Movie, MovieFile
from ..core.config import ConfigManager
from ..core.tmdb import TMDBClient

class MovieService:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.media_extensions = config_manager.settings.media_extension.split(';')
        self.subtitle_extensions = config_manager.settings.subtitle_extension.split(';')
        self.tmdb_client = TMDBClient(config_manager)

    async def scan_directory(self, root_path: str) -> List[Movie]:
        """Scan directory and build movie structure"""
        movies = []
        
        # Get all directories in the root path
        for item in os.listdir(root_path):
            item_path = os.path.join(root_path, item)
            if os.path.isdir(item_path):
                # Try to identify movie from directory name
                movie_info = await self._identify_movie_from_directory(item_path)
                if movie_info:
                    movie = await self._scan_movie_directory(item_path, movie_info)
                    movies.append(movie)
        
        return movies

    async def _identify_movie_from_directory(self, directory_path: str) -> Optional[Dict]:
        """Try to identify movie from directory name using TMDB"""
        directory_name = os.path.basename(directory_path)
        # Remove common movie indicators
        clean_name = re.sub(r'\([0-9]{4}\)|\[.*?\]|\(.*?\)', '', directory_name).strip()
        # Search TMDB for the movie
        results = await self.tmdb_client.search_movie(clean_name)
        if results and len(results) > 0:
            return results[0]
        return None

    async def _scan_movie_directory(self, directory_path: str, movie_info: Dict) -> Movie:
        """Scan a movie directory and identify files"""
        movie = Movie(
            tmdb_id=str(movie_info.get('id')),
            title=movie_info.get('title'),
            year=movie_info.get('release_date', '').split('-')[0],
            directory_path=directory_path,
            movie_info=movie_info
        )
        
        # Get all files in the directory
        files = os.listdir(directory_path)
        
        # Find the main media file
        media_file = next(
            (f for f in files if any(f.lower().endswith(ext.lower()) 
                                   for ext in self.media_extensions)),
            None
        )
        
        if media_file:
            # Find associated subtitle files
            subtitle_files = [
                f for f in files if any(f.lower().endswith(ext.lower()) 
                                      for ext in self.subtitle_extensions)
            ]
            
            file_path = os.path.join(directory_path, media_file)
            movie_file = MovieFile(
                file_path=file_path,
                file_name=media_file,
                file_size=os.path.getsize(file_path),
                modified_time=datetime.fromtimestamp(os.path.getmtime(file_path)),
                subtitles=subtitle_files
            )
            movie.files.append(movie_file)
        
        return movie

    async def identify_movies(self, movies: List[Movie]) -> List[Movie]:
        """Identify all movies"""
        identified_movies = []
        
        for movie in movies:
            if not movie.tmdb_id:
                continue
                
            # Get detailed movie info from TMDB
            movie_info = await self._get_movie_info(movie.tmdb_id)
            if movie_info:
                movie.movie_info = movie_info
                identified_movies.append(movie)
        
        return identified_movies

    async def _get_movie_info(self, movie_id: str) -> Optional[Dict]:
        """Get movie information from TMDB"""
        try:
            return await self.tmdb_client.get_movie(movie_id)
        except Exception as e:
            print(f"Error getting movie info: {e}")
            return None

    async def rename_movies(self, movies: List[Movie]) -> List[Dict]:
        """Rename all movies following movie naming convention"""
        results = []
        
        for movie in movies:
            if not movie.selected:
                continue
            
            for movie_file in movie.files:
                if not movie_file.selected:
                    continue
                
                # Generate new movie name
                new_name = self._generate_movie_name(
                    movie.title,
                    movie.year,
                    movie.movie_info
                )
                
                # Rename main file
                new_path = os.path.join(movie.directory_path, new_name)
                result = await self._rename_file(movie_file.file_path, new_path)
                results.append(result)
                
                # Rename subtitle files
                for subtitle in movie_file.subtitles:
                    subtitle_path = os.path.join(
                        os.path.dirname(movie_file.file_path),
                        subtitle
                    )
                    new_subtitle = self._generate_subtitle_name(
                        new_name,
                        subtitle
                    )
                    new_subtitle_path = os.path.join(
                        movie.directory_path,
                        new_subtitle
                    )
                    result = await self._rename_file(
                        subtitle_path,
                        new_subtitle_path
                    )
                    results.append(result)
        
        return results

    def _generate_movie_name(
        self,
        title: str,
        year: str,
        movie_info: Dict
    ) -> str:
        """Generate standardized movie name"""
        return f"{title} ({year})"

    def _generate_subtitle_name(
        self,
        movie_name: str,
        subtitle_file: str
    ) -> str:
        """Generate subtitle name matching movie name"""
        # Extract language code from original subtitle name
        lang_code = self._extract_language_code(subtitle_file)
        # Remove extension from movie name
        base_name = os.path.splitext(movie_name)[0]
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