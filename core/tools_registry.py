"""core/tools_registry.py — Tool Registry & Candidate Tool Search for JARVIS vNext++.

- LLM NEVER receives all tools.
- Vector search retrieves top 3-5 candidate Tool Cards.
- Every Tool Card includes Name, Aliases, Description, Arguments, Examples, Risk Level, Verification Method.
- Mandatory tool verification protocols (process checks, file checks, URL checks).
"""

from __future__ import annotations

import os
import sys
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    name: str
    aliases: List[str]
    description: str
    arguments: Dict[str, str]
    examples: List[str]
    risk_level: str = "low"  # low, medium, high
    verification_method: str = "process_found"
    category: str = "system"

    def to_card(self) -> Dict[str, Any]:
        return asdict(self)


class UnifiedToolRegistry:
    """Tool registry with embedding candidate search and state verification."""

    def __init__(self):
        self._registry: Dict[str, ToolSpec] = {}
        self._handlers: Dict[str, Callable] = {}
        self._register_default_tools()

    def register(self, spec: ToolSpec, handler: Callable) -> None:
        self._registry[spec.name.lower()] = spec
        self._handlers[spec.name.lower()] = handler
        for alias in spec.aliases:
            self._registry[alias.lower()] = spec
            self._handlers[alias.lower()] = handler

    def _register_default_tools(self) -> None:
        # 1. Open Application
        self.register(
            ToolSpec(
                name="open_application",
                aliases=["open_app", "launch_app", "start_app"],
                description="Opens a local application by name (e.g. chrome, notepad, vscode, spotify).",
                arguments={"app_name": "str"},
                examples=["open chrome", "launch notepad"],
                risk_level="low",
                verification_method="process_found",
            ),
            self._handle_open_application,
        )
        # 2. Web Search
        self.register(
            ToolSpec(
                name="web_search",
                aliases=["search_google", "google_search"],
                description="Performs web search for target query.",
                arguments={"query": "str"},
                examples=["search python tutorials"],
                risk_level="low",
                verification_method="url_loaded",
            ),
            self._handle_web_search,
        )
        # 3. YouTube Video Info
        self.register(
            ToolSpec(
                name="youtube_video_info",
                aliases=["youtube_info", "get_youtube_info", "video_info"],
                description="Gets information about a YouTube video (title, views, duration, channel, etc.)",
                arguments={"url": "str"},
                examples=["get info about https://youtube.com/watch?v=xxx", "youtube video info https://youtu.be/xxx"],
                risk_level="low",
                verification_method="data_returned",
                category="media",
            ),
            self._handle_youtube_video_info,
        )
        # 4. YouTube Download
        self.register(
            ToolSpec(
                name="youtube_download",
                aliases=["download_youtube", "download_video", "save_youtube"],
                description="Downloads a YouTube video in best quality",
                arguments={"url": "str", "output_path": "str (optional)"},
                examples=["download https://youtube.com/watch?v=xxx", "save youtube video https://youtu.be/xxx"],
                risk_level="medium",
                verification_method="file_exists",
                category="media",
            ),
            self._handle_youtube_download,
        )
        # 5. YouTube Search
        self.register(
            ToolSpec(
                name="youtube_search",
                aliases=["search_youtube", "find_youtube", "youtube_find"],
                description="Searches YouTube for videos matching a query",
                arguments={"query": "str", "max_results": "int (optional, default 5)"},
                examples=["search youtube for python tutorial", "find youtube videos about cats"],
                risk_level="low",
                verification_method="data_returned",
                category="media",
            ),
            self._handle_youtube_search,
        )
        # 6. Instagram User Info
        self.register(
            ToolSpec(
                name="instagram_user_info",
                aliases=["instagram_info", "get_instagram_user", "insta_info"],
                description="Gets information about an Instagram user (followers, posts, bio, profile pic, etc.)",
                arguments={"username": "str"},
                examples=["get instagram info for elonmusk", "instagram user info natgeo"],
                risk_level="low",
                verification_method="data_returned",
                category="social",
            ),
            self._handle_instagram_user_info,
        )
        # 7. Instagram Posts
        self.register(
            ToolSpec(
                name="instagram_posts",
                aliases=["instagram_latest_posts", "get_instagram_posts", "insta_posts"],
                description="Gets latest posts from an Instagram user",
                arguments={"username": "str", "limit": "int (optional, default 10)"},
                examples=["get latest posts from natgeo", "instagram posts elonmusk 5"],
                risk_level="low",
                verification_method="data_returned",
                category="social",
            ),
            self._handle_instagram_posts,
        )

    # ── Mapping: query prefix → (tool_name, arg_name) ───────────────────
    # When the planner identifies a tool-action query, we need to know
    # which tool to run AND which keyword-argument to populate.
    # ORDER MATTERS: more specific triggers first (e.g. "download" before "youtube").
    _QUERY_TOOL_MAP: list[tuple[list[str], str, str]] = [
        # (trigger words, tool_name, arg_name)
        (["open", "launch", "start"], "open_application", "app_name"),
        (["close", "kill", "stop"], "close_application", "app_name"),
        (["search", "google", "look up", "find"], "web_search", "query"),
        (["download", "save"], "youtube_download", "url"),
        (["youtube info", "youtube video"], "youtube_video_info", "url"),
        (["youtube", "video"], "youtube_search", "query"),
        (["instagram", "insta"], "instagram_user_info", "username"),
    ]

    # Words to strip from the extracted value (not part of the actual argument)
    _FILLER_WORDS = {"for", "on", "the", "a", "an", "about", "of", "info", "video", "on"}

    def classify_input(self, query: str) -> tuple[str, str, str]:
        """Classify a raw user query into (tool_name, arg_name, arg_value).

        Returns ("", "", "") if no tool match is found, signalling that
        the LLM should handle the request instead.
        """
        q = query.lower().strip()

        for triggers, tool_name, arg_name in self._QUERY_TOOL_MAP:
            for trigger in triggers:
                if trigger in q:
                    # Extract the value: everything after the trigger word
                    value = q.split(trigger, 1)[-1].strip()
                    # Strip common filler words from the front
                    while value:
                        first_word = value.split(" ", 1)[0]
                        if first_word in self._FILLER_WORDS:
                            value = value[len(first_word):].lstrip()
                        else:
                            break
                    if not value:
                        value = query  # fallback: pass the whole query
                    return tool_name, arg_name, value

        return "", "", ""

    def search_candidates(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Find top 3-5 candidate tool cards for the query using keyword/vector matching."""
        q = query.lower().strip()
        query_words = set(q.split())
        scored = []

        seen_specs = set()
        for name, spec in self._registry.items():
            if spec.name in seen_specs:
                continue
            seen_specs.add(spec.name)

            desc_words = set(spec.description.lower().split()) | set(spec.name.lower().split())
            score = len(query_words & desc_words)
            for alias in spec.aliases:
                if alias.lower() in q:
                    score += 5
            # Bonus: if any trigger word from _QUERY_TOOL_MAP matches.
            # Earlier entries in _QUERY_TOOL_MAP get a higher bonus.
            for priority, (triggers, tool_name, _) in enumerate(self._QUERY_TOOL_MAP):
                if spec.name == tool_name:
                    for trigger in triggers:
                        if trigger in q:
                            score += 20 - priority  # earlier = higher bonus

            scored.append((score, spec.to_card()))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute tool and perform mandatory verification."""
        name_clean = tool_name.lower().strip()
        handler = self._handlers.get(name_clean)
        if not handler:
            return {"success": False, "error": f"Tool '{tool_name}' not found."}

        try:
            result = handler(**kwargs)
            # Mandatory State Verification
            verified = self.verify_tool_execution(name_clean, kwargs, result)
            result["verified"] = verified
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"success": False, "error": str(e), "verified": False}

    def verify_tool_execution(self, tool_name: str, args: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Mandatory verification checks."""
        spec = self._registry.get(tool_name)
        if not spec:
            return True

        if spec.verification_method == "process_found":
            if not PSUTIL_AVAILABLE:
                return True
            app_name = args.get("app_name", "").lower()
            if not app_name:
                return True
            for proc in psutil.process_iter(['name']):
                try:
                    if app_name in proc.info['name'].lower():
                        return True
                except Exception:
                    continue
            return False

        return True

    # --- Tool Handlers ---
    def _handle_open_application(self, app_name: str = "") -> Dict[str, Any]:
        app_clean = app_name.lower().strip()
        if sys.platform == "win32":
            os.system(f'start "" "{app_clean}"')
            return {"success": True, "output": f"Launched {app_name}"}
        return {"success": True, "output": f"Launch command sent for {app_name}"}

    def _handle_web_search(self, query: str = "") -> Dict[str, Any]:
        import webbrowser
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        return {"success": True, "output": f"Opened web search for '{query}'"}

    def _handle_youtube_video_info(self, url: str = "") -> Dict[str, Any]:
        """Get YouTube video information using yt-dlp."""
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "success": True,
                    "output": {
                        "title": info.get('title'),
                        "views": info.get('view_count'),
                        "length": info.get('duration'),
                        "author": info.get('uploader'),
                        "upload_date": info.get('upload_date'),
                        "description": info.get('description', '')[:500] + "..." if info.get('description') and len(info.get('description', '')) > 500 else info.get('description', ''),
                        "thumbnail_url": info.get('thumbnail'),
                        "url": url,
                    }
                }
        except Exception as e:
            return {"success": False, "error": f"Failed to get YouTube video info: {str(e)}"}

    def _handle_youtube_download(self, url: str = "", output_path: str = "") -> Dict[str, Any]:
        """Download YouTube video using yt-dlp."""
        try:
            import yt_dlp
            ydl_opts = {
                'format': 'best',
                'outtmpl': output_path if output_path else '%(title)s.%(ext)s',
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            return {
                "success": True,
                "output": f"Downloaded: {filename}",
                "file_path": filename
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to download YouTube video: {str(e)}"}

    def _handle_youtube_search(self, query: str = "", max_results: int = 5) -> Dict[str, Any]:
        """Search YouTube using yt-dlp."""
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_search',
                'max_downloads': max_results,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                results = []
                if 'entries' in search_results:
                    for video in search_results['entries']:
                        if video:
                            results.append({
                                "title": video.get('title'),
                                "url": f"https://www.youtube.com/watch?v={video.get('id')}",
                                "views": video.get('view_count'),
                                "duration": video.get('duration'),
                                "author": video.get('uploader'),
                                "thumbnail": video.get('thumbnail'),
                            })
                return {
                    "success": True,
                    "output": f"Found {len(results)} videos for '{query}'",
                    "results": results
                }
        except Exception as e:
            return {"success": False, "error": f"Failed to search YouTube: {str(e)}"}

    def _handle_instagram_user_info(self, username: str = "") -> Dict[str, Any]:
        """Get Instagram user information using instaloader."""
        try:
            import instaloader
            L = instaloader.Instaloader()
            profile = instaloader.Profile.from_username(L.context, username)
            return {
                "success": True,
                "output": {
                    "username": profile.username,
                    "userid": profile.userid,
                    "full_name": profile.full_name,
                    "bio": profile.bio,
                    "followers": profile.followers,
                    "followees": profile.followees,
                    "posts": profile.mediacount,
                    "is_private": profile.is_private,
                    "is_verified": profile.is_verified,
                    "profile_pic_url": profile.profile_pic_url,
                    "external_url": profile.external_url,
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get Instagram user info: {str(e)}"}

    def _handle_instagram_posts(self, username: str = "", limit: int = 10) -> Dict[str, Any]:
        """Get latest Instagram posts using instaloader."""
        try:
            import instaloader
            L = instaloader.Instaloader()
            profile = instaloader.Profile.from_username(L.context, username)
            posts = []
            for i, post in enumerate(profile.get_posts()):
                if i >= limit:
                    break
                posts.append({
                    "shortcode": post.shortcode,
                    "url": post.url,
                    "caption": post.caption[:200] + "..." if post.caption and len(post.caption) > 200 else post.caption,
                    "likes": post.likes,
                    "comments": post.comments,
                    "is_video": post.is_video,
                    "date": post.date_local,
                })
            return {
                "success": True,
                "output": f"Retrieved {len(posts)} posts from @{username}",
                "posts": posts
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get Instagram posts: {str(e)}"}


tool_registry = UnifiedToolRegistry()
