"""jarvis.entertainment

Entertainment features: Spotify, Netflix, YouTube control, music suggestions.
"""

from __future__ import annotations

import logging
import random
import subprocess
from dataclasses import dataclass
from typing import Any

from jarvis.secure_storage import secure_storage
from jarvis.tools import play_youtube, play_music

logger = logging.getLogger(__name__)


@dataclass
class Song:
    """Song information."""
    title: str
    artist: str
    album: str
    duration_ms: int
    uri: str


class SpotifyController:
    """Spotify integration via Spotify Web API."""
    
    def __init__(self) -> None:
        self.sp = None
        self._init_spotify()
    
    def _init_spotify(self) -> None:
        """Initialize Spotify client."""
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            
            client_id = secure_storage.get("SPOTIFY_CLIENT_ID")
            client_secret = secure_storage.get("SPOTIFY_CLIENT_SECRET")
            
            if client_id and client_secret:
                self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri="http://localhost:8888/callback",
                    scope="user-read-playback-state,user-modify-playback-state,user-read-currently-playing,playlist-read-private",
                ))
        except Exception as e:
            logger.error(f"Failed to init Spotify: {e}")
    
    def is_available(self) -> bool:
        return self.sp is not None
    
    def get_current_track(self) -> dict[str, Any] | None:
        """Get currently playing track."""
        if not self.sp:
            return None
        
        try:
            current = self.sp.current_playback()
            if current and current.get("item"):
                item = current["item"]
                return {
                    "title": item.get("name", "Unknown"),
                    "artist": ", ".join(a["name"] for a in item.get("artists", [])),
                    "album": item.get("album", {}).get("name", "Unknown"),
                    "is_playing": current.get("is_playing", False),
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get current track: {e}")
            return None
    
    def play(self, context_uri: str | None = None) -> bool:
        """Start playback."""
        if not self.sp:
            return False
        
        try:
            if context_uri:
                self.sp.start_playback(context_uri=context_uri)
            else:
                self.sp.start_playback()
            return True
        except Exception as e:
            logger.error(f"Failed to play: {e}")
            return False
    
    def pause(self) -> bool:
        """Pause playback."""
        if not self.sp:
            return False
        
        try:
            self.sp.pause_playback()
            return True
        except Exception as e:
            logger.error(f"Failed to pause: {e}")
            return False
    
    def next_track(self) -> bool:
        """Skip to next track."""
        if not self.sp:
            return False
        
        try:
            self.sp.next_track()
            return True
        except Exception as e:
            logger.error(f"Failed to skip: {e}")
            return False
    
    def previous_track(self) -> bool:
        """Go to previous track."""
        if not self.sp:
            return False
        
        try:
            self.sp.previous_track()
            return True
        except Exception as e:
            logger.error(f"Failed to go back: {e}")
            return False
    
    def set_volume(self, volume: int) -> bool:
        """Set playback volume (0-100)."""
        if not self.sp:
            return False
        
        try:
            self.sp.volume(volume)
            return True
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False
    
    def search_and_play(self, query: str, type_: str = "track") -> str:
        """Search and play."""
        if not self.sp:
            return "Spotify not connected"
        
        try:
            results = self.sp.search(q=query, type=type_, limit=1)
            
            if type_ == "track" and results["tracks"]["items"]:
                track = results["tracks"]["items"][0]
                self.sp.start_playback(uris=[track["uri"]])
                return f"Playing: {track['name']} by {track['artists'][0]['name']}"
            
            elif type_ == "playlist" and results["playlists"]["items"]:
                playlist = results["playlists"]["items"][0]
                self.sp.start_playback(context_uri=playlist["uri"])
                return f"Playing playlist: {playlist['name']}"
            
            return "No results found"
            
        except Exception as e:
            return f"Failed to play: {e}"
    
    def get_my_playlists(self) -> list[dict[str, Any]]:
        """Get user's playlists."""
        if not self.sp:
            return []
        
        try:
            playlists = self.sp.current_user_playlists()
            return [
                {"name": p["name"], "id": p["id"], "tracks": p["tracks"]["total"]}
                for p in playlists.get("items", [])
            ]
        except Exception as e:
            logger.error(f"Failed to get playlists: {e}")
            return []
    
    def get_liked_songs(self) -> list[dict[str, Any]]:
        """Get liked songs."""
        if not self.sp:
            return []
        
        try:
            results = self.sp.current_user_saved_tracks(limit=20)
            return [
                {
                    "name": t["track"]["name"],
                    "artist": t["track"]["artists"][0]["name"],
                }
                for t in results.get("items", [])
            ]
        except Exception as e:
            logger.error(f"Failed to get liked songs: {e}")
            return []


class MoodMusicRecommender:
    """Recommend music based on mood."""
    
    MOOD_PLAYLISTS = {
        "happy": [
            "spotify:playlist:37i9dQZF1DX3rxVfCZqE7N",  # Happy Hits
            "uplifting pop music",
        ],
        "sad": [
            "spotify:playlist:37i9dQZF1DX7qK8ma5wgY2",  # Sad Songs
            "melancholic acoustic",
        ],
        "energetic": [
            "spotify:playlist:37i9dQZF1DX76Wlfdnj7AP",  # Beast Mode
            "workout motivation",
        ],
        "relaxed": [
            "spotify:playlist:37i9dQZF1DX4wta20PHgwo",  # Deep Focus
            "chill lofi beats",
        ],
        "focused": [
            "spotify:playlist:37i9dQZF1DX5trt9i14Xb",  # Peaceful Piano
            "instrumental study music",
        ],
        "romantic": [
            "spotify:playlist:37i9dQZF1DX4P1C3veacT",  # Love Pop
            "love songs",
        ],
        "party": [
            "spotify:playlist:37i9dQZF1DXa2PvUpywm6",  # Party Hits
            "dance party music",
        ],
    }
    
    def __init__(self, spotify: SpotifyController) -> None:
        self.spotify = spotify
    
    def recommend(self, mood: str) -> str:
        """Recommend music for mood."""
        mood = mood.lower()
        
        if mood not in self.MOOD_PLAYLISTS:
            return f"Unknown mood. Try: {', '.join(self.MOOD_PLAYLISTS.keys())}"
        
        options = self.MOOD_PLAYLISTS[mood]
        
        # Try Spotify first
        if self.spotify.is_available():
            playlist_uri = options[0]
            if self.spotify.play(playlist_uri):
                return f"Playing {mood} playlist on Spotify"
        
        # Fallback to YouTube
        query = options[1]
        return play_music(query)


class NetflixController:
    """Netflix control via browser automation."""
    
    def __init__(self) -> None:
        self.email = secure_storage.get("NETFLIX_EMAIL")
        self.password = secure_storage.get("NETFLIX_PASSWORD")
    
    def open_netflix(self, search: str | None = None) -> str:
        """Open Netflix in browser."""
        import webbrowser
        
        if search:
            url = f"https://www.netflix.com/search?q={search.replace(' ', '+')}"
        else:
            url = "https://www.netflix.com/browse"
        
        webbrowser.open(url)
        return f"Opening Netflix{' with search: ' + search if search else ''}"
    
    def search_and_play(self, title: str) -> str:
        """Search and open a title."""
        return self.open_netflix(title)


class GameLauncher:
    """Launch games with voice."""
    
    GAME_PATHS = {
        "minecraft": ["minecraft"],
        "valorant": ["C:\\Riot Games\\VALORANT\\live\\VALORANT.exe"],
        "fortnite": ["fortnite"],
        "gta": ["steam://rungameid/271590"],  # GTA V
        "csgo": ["steam://rungameid/730"],
        "cod": ["call of duty"],
        "apex": ["apex legends"],
        "rocket league": ["steam://rungameid/252950"],
    }
    
    def launch_game(self, game_name: str) -> str:
        """Launch a game."""
        game_name = game_name.lower()
        
        # Find matching game
        for name, paths in self.GAME_PATHS.items():
            if name in game_name or game_name in name:
                try:
                    if paths[0].startswith("steam://"):
                        import webbrowser
                        webbrowser.open(paths[0])
                    else:
                        subprocess.Popen(paths)
                    return f"Launching {name}..."
                except Exception as e:
                    return f"Failed to launch {name}: {e}"
        
        # Try Steam search
        import webbrowser
        webbrowser.open(f"steam://store/search/?term={game_name.replace(' ', '+')}")
        return f"Searching for {game_name} on Steam"
    
    def list_games(self) -> str:
        """List available games."""
        games = list(self.GAME_PATHS.keys())
        return f"Available games: {', '.join(games)}"


class AudioVisualizer:
    """Simple audio visualization support."""
    
    def __init__(self) -> None:
        self.is_active = False
    
    def start_visualizer(self) -> str:
        """Start audio visualizer."""
        self.is_active = True
        # Would integrate with actual visualizer app
        return "Audio visualizer started (visualization would appear in GUI)"
    
    def stop_visualizer(self) -> str:
        """Stop audio visualizer."""
        self.is_active = False
        return "Audio visualizer stopped"


class PodcastPlayer:
    """Podcast streaming support."""
    
    PODCAST_FEEDS = {
        "tech": ["https://feeds.megaphone.fm/replyall"],
        "news": ["https://feeds.npr.org/510289/podcast.xml"],
        "comedy": ["https://feeds.feedburner.com/comedybangbang"],
        "science": ["https://feeds.megaphone.fm/sciencevs"],
        "business": ["https://feeds.megaphone.fm/howibuiltthis"],
    }
    
    def play_podcast(self, category: str, episode: int = 0) -> str:
        """Play a podcast."""
        category = category.lower()
        
        if category not in self.PODCAST_FEEDS:
            return f"Category not found. Try: {', '.join(self.PODCAST_FEEDS.keys())}"
        
        feed_url = self.PODCAST_FEEDS[category][0]
        
        # Open in browser or podcast app
        import webbrowser
        webbrowser.open(feed_url)
        
        return f"Opening {category} podcast"
    
    def search_podcast(self, query: str) -> str:
        """Search for podcasts."""
        import webbrowser
        webbrowser.open(f"https://open.spotify.com/search/{query.replace(' ', '%20')}/podcasts")
        return f"Searching podcasts for: {query}"


# Global instances
spotify = SpotifyController()
mood_recommender = MoodMusicRecommender(spotify)
netflix = NetflixController()
game_launcher = GameLauncher()
visualizer = AudioVisualizer()
podcast_player = PodcastPlayer()


def play_spotify(query: str) -> str:
    """Play on Spotify."""
    return spotify.search_and_play(query)


def play_for_mood(mood: str) -> str:
    """Play music for mood."""
    return mood_recommender.recommend(mood)


def launch_game(game: str) -> str:
    """Launch a game."""
    return game_launcher.launch_game(game)


def watch_netflix(title: str | None = None) -> str:
    """Watch Netflix."""
    return netflix.open_netflix(title)


def play_podcast(category: str) -> str:
    """Play podcast."""
    return podcast_player.play_podcast(category)
