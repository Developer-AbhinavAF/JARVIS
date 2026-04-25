"""jarvis.tools

Tool functions JARVIS can call via the LLM.

This module contains lightweight tools for web search, plotting charts,
opening apps/URLs, and getting the local datetime. A TOOL_REGISTRY maps the
LLM tool name to the Python callable.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import threading
import webbrowser
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from jarvis import config
from jarvis.system_control import SYSTEM_CONTROL_REGISTRY
from jarvis.dashboard import DASHBOARD_REGISTRY
from jarvis.memory import MEMORY_REGISTRY
from jarvis.plugins import PLUGIN_REGISTRY

logger = logging.getLogger(__name__)


def web_search(query: str) -> str:
    """Search the web and return a concise answer/snippet summary."""

    query = (query or "").strip()
    if not query:
        return "No query provided."

    # a) Tavily (preferred) for compact answers.
    api_key = (config.TAVILY_API_KEY or "").strip()
    if api_key and api_key != "YOUR_TAVILY_API_KEY":
        try:
            logger.info("Searching Tavily for: %s", query[:50])
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": 5,
                    "include_answer": True,
                },
                headers=config.SCRAPE_HEADERS,
                timeout=config.SCRAPE_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            answer = (data.get("answer") or "").strip()
            if answer:
                logger.info("Tavily returned answer: %s", answer[:50])
                return f"According to search results: {answer[:config.MAX_SNIPPET_CHARS]}"

            results = data.get("results") or []
            if results:
                snippets: list[str] = []
                for r in results[:3]:
                    title = (r.get("title") or "").strip()
                    content = (r.get("content") or "").strip()
                    url = (r.get("url") or "").strip()
                    if content:
                        if title:
                            snippets.append(f"{title}: {content}")
                        else:
                            snippets.append(content)

                joined = "\n\n".join(snippets).strip()
                if joined:
                    return f"Search results:\n{joined[:config.MAX_SNIPPET_CHARS]}"
            
            logger.warning("Tavily returned no results for: %s", query)
        except Exception as e:
            logger.exception("Tavily search failed: %s", str(e))
    else:
        logger.warning("No Tavily API key configured")

    # b) DuckDuckGo HTML fallback.
    try:
        logger.info("Falling back to DuckDuckGo for: %s", query[:50])
        url = "https://html.duckduckgo.com/html/"
        resp = requests.get(
            url,
            params={"q": query},
            headers=config.SCRAPE_HEADERS,
            timeout=config.SCRAPE_TIMEOUT,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        
        # Try multiple selectors for results
        snippets = []
        
        # Selector 1: result snippets
        for div in soup.select("div.result__snippet"):
            text = div.get_text(" ", strip=True)
            if text and len(text) > 20:
                snippets.append(text)
        
        # Selector 2: web results
        if not snippets:
            for result in soup.select(".web-result"):
                text = result.get_text(" ", strip=True)
                if text and len(text) > 20:
                    snippets.append(text[:200])
        
        # Selector 3: any result div
        if not snippets:
            for div in soup.select(".result"):
                text = div.get_text(" ", strip=True)
                if text and len(text) > 20:
                    snippets.append(text[:200])

        snippets = [s for s in snippets if s]

        if snippets:
            joined = "\n\n".join(snippets[:4]).strip()
            return f"Search results:\n{joined[:config.MAX_SNIPPET_CHARS]}"
        
        logger.warning("DuckDuckGo returned no results")
        return "No search results found. The search service may be temporarily unavailable."
        
    except Exception as e:
        logger.exception("DuckDuckGo search failed: %s", str(e))
        
    # c) Google direct link fallback
    try:
        encoded_query = requests.utils.quote(query)
        google_url = f"https://www.google.com/search?q={encoded_query}"
        return f"Search services unavailable. Here's a Google search link:\n{google_url}"
    except:
        pass
    
    return "Web search failed. Please check your internet connection or try again later."


def plot_chart(chart_type: str, title: str, labels: list[str], values: list[float], save_path: str = None) -> str:
    """Create a chart and save to file for frontend display.
    
    Args:
        chart_type: bar, line, or pie
        title: Chart title
        labels: Data labels
        values: Data values
        save_path: Optional path to save image (auto-generated if not provided)
        
    Returns:
        Path to saved chart image
    """
    import os
    from datetime import datetime

    if labels is None or values is None or len(labels) != len(values):
        return "Invalid chart data: labels and values must be the same length."
    
    # Auto-generate save path in JARVIS root (persistent across restarts)
    if not save_path:
        graphs_dir = os.path.join(config.JARVIS_ROOT, "graphs")
        os.makedirs(graphs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(graphs_dir, f"chart_{chart_type}_{timestamp}.png")

    df = pd.DataFrame({"label": labels, "value": values})
    chart_type = (chart_type or "").strip().lower()

    try:
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(10, 6))

        # Dark themed figure background
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#1a1a2e")

        cmap = plt.get_cmap("cool")

        if chart_type == "bar":
            colors = [cmap(i / max(1, len(df) - 1)) for i in range(len(df))]
            ax.bar(df["label"], df["value"], color=colors, edgecolor='white')
            ax.set_ylabel("Value")
            ax.grid(True, alpha=0.3, axis='y')
        elif chart_type == "line":
            ax.plot(df["label"], df["value"], color=cmap(0.7), marker="o", linewidth=2, markersize=8)
            ax.set_ylabel("Value")
            ax.grid(True, alpha=0.3)
        elif chart_type == "pie":
            colors = [cmap(i / max(1, len(df) - 1)) for i in range(len(df))]
            ax.pie(df["value"], labels=df["label"], colors=colors, autopct="%1.1f%%", startangle=90)
        else:
            return f"Unsupported chart type: {chart_type}. Use bar, line, or pie."

        ax.set_title(title or "Chart", color='white', fontsize=14, fontweight='bold')
        fig.tight_layout()
        
        # Save to file
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
        plt.close(fig)
        
        logger.info(f"✅ Chart saved to: {save_path}")
        return f"📊 {chart_type.title()} chart created! Image saved at: {save_path}"
        
    except Exception as e:
        logger.exception("Chart plotting failed")
        return f"Chart error: {str(e)}"


def open_app(target: str) -> str:
    """Open a URL or a known application target."""

    target = (target or "").strip()
    if not target:
        return "No target provided."

    system = platform.system().lower()

    # Expanded app map with common Windows apps and their process names
    app_map: dict[str, list[str]] = {
        # Windows built-in apps
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "terminal": ["wt.exe", "cmd.exe"],
        "cmd": ["cmd.exe"],
        "command prompt": ["cmd.exe"],
        "files": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
        "explorer": ["explorer.exe"],
        "settings": ["ms-settings:"],
        "control panel": ["control.exe"],
        "task manager": ["taskmgr.exe"],
        "paint": ["mspaint.exe"],
        "wordpad": ["wordpad.exe"],
        "powershell": ["powershell.exe"],
        "snipping tool": ["SnippingTool.exe"],
        
        # Browsers - try multiple possible paths
        "chrome": ["chrome.exe", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"],
        "google chrome": ["chrome.exe", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"],
        "firefox": ["firefox.exe", "C:\\Program Files\\Mozilla Firefox\\firefox.exe", "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"],
        "mozilla firefox": ["firefox.exe"],
        "edge": ["msedge.exe", "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"],
        "microsoft edge": ["msedge.exe"],
        "browser": ["chrome.exe", "firefox.exe", "msedge.exe"],
        
        # Communication apps
        "discord": ["Discord.exe", "C:\\Users\\%USERNAME%\\AppData\\Local\\Discord\\app-*\\Discord.exe"],
        "whatsapp": ["WhatsApp.exe"],
        "telegram": ["Telegram.exe"],
        "teams": ["teams.exe", "C:\\Users\\%USERNAME%\\AppData\\Local\\Microsoft\\Teams\\current\\Teams.exe"],
        "microsoft teams": ["teams.exe"],
        "skype": ["skype.exe"],
        "zoom": ["zoom.exe"],
        "slack": ["slack.exe"],
        
        # Media apps
        "spotify": ["Spotify.exe", "C:\\Users\\%USERNAME%\\AppData\\Roaming\\Spotify\\Spotify.exe"],
        "vlc": ["vlc.exe"],
        "media player": ["vlc.exe", "wmplayer.exe"],
        "itunes": ["itunes.exe"],
        
        # Office apps
        "word": ["winword.exe"],
        "microsoft word": ["winword.exe"],
        "excel": ["excel.exe"],
        "microsoft excel": ["excel.exe"],
        "powerpoint": ["powerpnt.exe"],
        "microsoft powerpoint": ["powerpnt.exe"],
        "outlook": ["outlook.exe"],
        "microsoft outlook": ["outlook.exe"],
        "onenote": ["onenote.exe"],
        
        # Development tools
        "vscode": ["code.exe", "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\bin\\code.cmd"],
        "visual studio code": ["code.exe"],
        "notepad++": ["notepad++.exe"],
        "sublime": ["sublime_text.exe"],
        
        # Utilities
        "obs": ["obs64.exe", "obs32.exe"],
        "steam": ["steam.exe"],
        "epic games": ["epicgameslauncher.exe"],
        
        # Linux (best-effort defaults)
        "gnome-settings": ["gnome-control-center"],
    }

    # URLs first.
    if target.startswith("http://") or target.startswith("https://"):
        try:
            webbrowser.open(target)
            return "Opening."
        except Exception:
            logger.exception("Failed to open URL")
            return "Failed to open the URL."

    key = target.lower()

    if key in app_map:
        # Try each possible command/path
        for cmd in app_map[key]:
            try:
                # Expand environment variables
                expanded_cmd = os.path.expandvars(cmd)
                
                # If it's a URL-like command (ms-settings:), use startfile
                if expanded_cmd.endswith(":") or expanded_cmd.startswith("ms-"):
                    os.startfile(expanded_cmd)
                    return f"Opening {target}."
                
                # Try to run the command
                # Use shell=False for .exe files (security), shell=True for commands
                use_shell = not expanded_cmd.endswith('.exe') and '.' not in os.path.basename(expanded_cmd)
                subprocess.Popen(expanded_cmd, shell=use_shell)
                return f"Opening {target}."
            except Exception as e:
                logger.debug("Failed to open %s with %s: %s", target, expanded_cmd, str(e))
                continue  # Try next option
        
        # If all direct attempts failed, try Windows 'start' command
        if system.startswith("windows"):
            try:
                subprocess.Popen(f"start {target}", shell=True)
                return f"Opening {target}."
            except Exception:
                logger.exception("Failed to start app: %s", target)
        
        return f"Failed to open {target}. Is it installed?"

    # If it looks like a domain, treat it as a URL.
    if "." in target and " " not in target:
        try:
            webbrowser.open("https://" + target)
            return "Opening."
        except Exception:
            logger.exception("Failed to open domain")
            return "Failed to open the website."

    # Final fallback: use Windows start command or xdg-open
    try:
        if system.startswith("windows"):
            # Use 'start' command for better app discovery
            subprocess.Popen(f"start \"{target}\"", shell=True)
        else:
            subprocess.Popen(["xdg-open", target])
        return f"Opening {target}."
    except Exception:
        logger.exception("Failed to open target: %s", target)
        return f"Failed to open {target}. Try the full app name or check if it's installed."


def close_app(target: str) -> str:
    """Close/terminate an application by name.
    
    Args:
        target: Application name (e.g., "notepad", "chrome", "calculator")
    """
    target = (target or "").strip().lower()
    if not target:
        return "No application name provided."

    system = platform.system().lower()

    # Common app process name mappings
    process_map: dict[str, list[str]] = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe", "calculator.exe"],
        "chrome": ["chrome.exe"],
        "firefox": ["firefox.exe"],
        "edge": ["msedge.exe"],
        "word": ["winword.exe"],
        "excel": ["excel.exe"],
        "powerpoint": ["powerpnt.exe"],
        "outlook": ["outlook.exe"],
        "teams": ["teams.exe"],
        "discord": ["discord.exe"],
        "spotify": ["spotify.exe"],
        "vlc": ["vlc.exe"],
        "cmd": ["cmd.exe"],
        "terminal": ["wt.exe", "cmd.exe"],
        "explorer": ["explorer.exe"],
    }

    processes_to_kill = process_map.get(target, [target])

    killed = []
    failed = []

    for proc_name in processes_to_kill:
        try:
            if system.startswith("windows"):
                # Try graceful close first (taskkill)
                result = subprocess.run(
                    ["taskkill", "/im", proc_name, "/f"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0 or "terminated" in result.stdout.lower():
                    killed.append(proc_name)
                else:
                    # Try with .exe suffix
                    if not proc_name.endswith(".exe"):
                        result2 = subprocess.run(
                            ["taskkill", "/im", proc_name + ".exe", "/f"],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result2.returncode == 0 or "terminated" in result2.stdout.lower():
                            killed.append(proc_name + ".exe")
                        else:
                            failed.append(proc_name)
                    else:
                        failed.append(proc_name)
            else:
                # Linux/Mac - use pkill
                result = subprocess.run(
                    ["pkill", "-f", proc_name],
                    capture_output=True,
                    check=False
                )
                if result.returncode == 0:
                    killed.append(proc_name)
                else:
                    failed.append(proc_name)
        except Exception as e:
            logger.exception("Failed to close app: %s", proc_name)
            failed.append(f"{proc_name} ({str(e)})")

    if killed:
        return f"Closed: {', '.join(killed)}"
    elif failed:
        return f"Could not close: {', '.join(failed)}. Try using 'kill process' with the exact process name."
    else:
        return f"Could not find or close '{target}'. Use 'list apps' to see running applications."


def list_running_apps(limit: int = 20) -> str:
    """List currently running applications/processes.
    
    Args:
        limit: Maximum number of apps to show (default 20)
    """
    try:
        import psutil
    except ImportError:
        return "Listing apps requires psutil. Run: pip install psutil"

    try:
        apps = []
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                info = proc.info
                # Only show processes that are actually running and have a window (Windows)
                # or just filter by common app patterns
                name = info['name'].lower()
                
                # Filter out system processes, show likely user apps
                system_processes = {
                    'svchost.exe', 'services.exe', 'lsass.exe', 'csrss.exe',
                    'smss.exe', 'wininit.exe', 'winlogon.exe', 'crss.exe',
                    'system', 'registry', 'memory compression', 'idle',
                    'dllhost.exe', 'conhost.exe', 'wmiprvse.exe'
                }
                
                if name not in system_processes and info['status'] == psutil.STATUS_RUNNING:
                    apps.append((info['name'], info['pid']))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Remove duplicates (same app name)
        seen = set()
        unique_apps = []
        for name, pid in apps:
            if name not in seen:
                seen.add(name)
                unique_apps.append((name, pid))

        # Sort and limit
        unique_apps.sort(key=lambda x: x[0])
        limited_apps = unique_apps[:limit]

        if not limited_apps:
            return "No user applications found running."

        lines = [f"{name} (PID: {pid})" for name, pid in limited_apps]
        return f"Running applications ({len(limited_apps)} shown):\n" + "\n".join(lines)

    except Exception as e:
        logger.exception("Failed to list apps")
        return f"Error listing apps: {str(e)}"


def kill_process(target: str, force: bool = True) -> str:
    """Force kill a process by name or PID.
    
    Args:
        target: Process name (e.g., "chrome.exe") or PID number
        force: If True, force kill (/f on Windows, -9 on Linux)
    """
    target = (target or "").strip()
    if not target:
        return "No process name or PID provided."

    try:
        import psutil
    except ImportError:
        return "Killing processes requires psutil. Run: pip install psutil"

    try:
        # Check if target is a PID (number)
        try:
            pid = int(target)
            # Kill by PID
            try:
                proc = psutil.Process(pid)
                name = proc.name()
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                return f"Killed process: {name} (PID: {pid})"
            except psutil.NoSuchProcess:
                return f"No process found with PID: {pid}"
        except ValueError:
            # Target is a name, not a PID
            pass

        # Kill by name
        killed = []
        target_lower = target.lower()
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if target_lower in proc.info['name'].lower():
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    killed.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            return f"Killed processes:\n" + "\n".join(killed)
        else:
            return f"No processes found matching '{target}'. Use 'list apps' to see running processes."

    except Exception as e:
        logger.exception("Failed to kill process")
        return f"Error killing process: {str(e)}"


def get_datetime() -> str:
    """Return the current local date/time as a human-friendly string."""

    try:
        return datetime.now().strftime("%A, %d %B %Y — %H:%M")
    except Exception:
        logger.exception("Datetime formatting failed")
        return "Unable to get the current date and time."


def search_youtube(query: str, max_results: int = 5) -> str:
    """Search YouTube for videos and return results with links.
    
    Args:
        query: Search query for YouTube videos
        max_results: Number of results to return (default 5)
    """
    query = (query or "").strip()
    if not query:
        return "No search query provided."

    try:
        # Use YouTube Data API if key available, otherwise use web scraping
        search_url = "https://www.youtube.com/results"
        params = {"search_query": query}
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        resp = requests.get(search_url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        
        # Extract video IDs and titles from HTML
        import re
        
        # Find video data in the response
        video_pattern = r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"([^"]+)"\}\]\}'
        matches = re.findall(video_pattern, resp.text)
        
        if not matches:
            # Try alternative pattern
            video_pattern2 = r'"videoId":"([a-zA-Z0-9_-]{11})"'
            video_ids = list(dict.fromkeys(re.findall(video_pattern2, resp.text)))[:max_results]
            
            if video_ids:
                results = []
                for i, vid in enumerate(video_ids, 1):
                    url = f"https://youtube.com/watch?v={vid}"
                    results.append(f"{i}. Video {i}: {url}")
                return "YouTube search results:\n" + "\n".join(results)
            
            return "Could not find YouTube videos for that query."
        
        # Format results
        results = []
        seen_ids = set()
        
        for vid_id, title in matches[:max_results]:
            if vid_id not in seen_ids and len(title) > 3:
                seen_ids.add(vid_id)
                # Clean up title
                title = title.encode('utf-8', errors='ignore').decode('utf-8')
                url = f"https://youtube.com/watch?v={vid_id}"
                results.append(f"{len(results)+1}. {title[:60]}: {url}")
        
        if results:
            return "YouTube search results:\n" + "\n".join(results)
        else:
            return "No YouTube videos found for that query."
            
    except Exception as e:
        logger.exception("YouTube search failed")
        # Fallback: return direct search URL
        encoded_query = requests.utils.quote(query)
        return f"YouTube search: https://www.youtube.com/results?search_query={encoded_query}"


def play_youtube(query: str) -> str:
    """Search YouTube and play the first video result in browser.
    
    Args:
        query: Video to search for (e.g., "Shape of You Ed Sheeran")
    """
    query = (query or "").strip()
    if not query:
        return "No video query provided. Say something like 'play Despacito'"

    try:
        # First search for the video
        search_url = "https://www.youtube.com/results"
        params = {"search_query": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        resp = requests.get(search_url, params=params, headers=headers, timeout=15)
        
        # Extract first video ID
        import re
        video_pattern = r'"videoId":"([a-zA-Z0-9_-]{11})"'
        video_ids = re.findall(video_pattern, resp.text)
        
        if not video_ids:
            # Try opening search directly
            encoded_query = requests.utils.quote(query)
            webbrowser.open(f"https://www.youtube.com/results?search_query={encoded_query}")
            return f"Opened YouTube search for: {query}"
        
        # Get first unique video
        first_video = video_ids[0]
        video_url = f"https://www.youtube.com/watch?v={first_video}"
        
        # Open in browser
        webbrowser.open(video_url)
        return f"Playing: {video_url}"
        
    except Exception as e:
        logger.exception("YouTube play failed")
        # Fallback to search
        try:
            encoded_query = requests.utils.quote(query)
            webbrowser.open(f"https://www.youtube.com/results?search_query={encoded_query}")
            return f"Opened YouTube search for: {query}"
        except:
            return f"Failed to play video. Try searching manually: https://youtube.com/results?search_query={requests.utils.quote(query)}"


def play_music(query: str) -> str:
    """Play music on YouTube Music or regular YouTube.
    
    Args:
        query: Song or artist to play (e.g., "Shape of You", "Ed Sheeran")
    """
    query = (query or "").strip()
    if not query:
        return "No song provided. Say something like 'play Shape of You'"
    
    # Add "music" or "song" to improve search if not present
    search_terms = query
    if not any(word in query.lower() for word in ["song", "music", "audio"]):
        search_terms = f"{query} official music video"
    
    return play_youtube(search_terms)


def play_video(query: str) -> str:
    """Play any video on YouTube.
    
    Args:
        query: Video to search for (e.g., "funny cat videos", "tutorial python")
    """
    return play_youtube(query)


def test_keyboard() -> str:
    """Test keyboard functionality by simulating a simple test pattern."""
    try:
        import pyautogui
        import time
        
        # Open notepad for testing
        subprocess.Popen("notepad.exe")
        time.sleep(1)
        
        # Type test message
        pyautogui.typewrite("""Keyboard Test - JARVIS
====================
Testing all keys...
1234567890
ABCDEFGHIJKLMNOPQRSTUVWXYZ
!@#$%^&*()
Test complete!""", interval=0.01)
        
        return "Keyboard test completed. Check Notepad for the test pattern."
    except Exception as e:
        logger.exception("Keyboard test failed")
        return f"Keyboard test failed: {str(e)}. Make sure pyautogui is installed."


def test_mouse() -> str:
    """Test mouse functionality by moving in a pattern."""
    try:
        import pyautogui
        import time
        
        # Get screen center
        screen_width, screen_height = pyautogui.size()
        center_x, center_y = screen_width // 2, screen_height // 2
        
        # Move in a square pattern around center
        pyautogui.moveTo(center_x - 100, center_y - 100, duration=0.5)
        time.sleep(0.2)
        pyautogui.moveTo(center_x + 100, center_y - 100, duration=0.5)
        time.sleep(0.2)
        pyautogui.moveTo(center_x + 100, center_y + 100, duration=0.5)
        time.sleep(0.2)
        pyautogui.moveTo(center_x - 100, center_y + 100, duration=0.5)
        time.sleep(0.2)
        pyautogui.moveTo(center_x, center_y, duration=0.5)
        
        # Click at center
        pyautogui.click(center_x, center_y)
        
        return f"Mouse test completed. Moved in square pattern around screen center ({center_x}, {center_y})."
    except Exception as e:
        logger.exception("Mouse test failed")
        return f"Mouse test failed: {str(e)}. Make sure pyautogui is installed."


def get_joke() -> str:
    """Get a random joke."""
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "Why did the computer show up at work late? It had a hard drive!",
        "What do you call a computer that sings? A Dell!",
        "Why do Java developers wear glasses? Because they don't C#!",
        "What's a computer's favorite snack? Microchips!",
        "Why was the cell phone wearing glasses? It lost its contacts!",
        "What do you call a computer floating in the ocean? A Dell Rolling in the Deep!",
        "Why did the PowerPoint presentation cross the road? To get to the other slide!",
        "What did the spider do on the computer? Made a website!",
        "Why was the computer cold? It left its Windows open!",
    ]
    import random
    return random.choice(jokes)


def get_quote() -> str:
    """Get an inspirational quote."""
    quotes = [
        "The only way to do great work is to love what you do. - Steve Jobs",
        "Innovation distinguishes between a leader and a follower. - Steve Jobs",
        "Stay hungry, stay foolish. - Steve Jobs",
        "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
        "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
        "The best time to plant a tree was 20 years ago. The second best time is now. - Chinese Proverb",
        "Your limitation is only your imagination.",
        "Push yourself, because no one else is going to do it for you.",
        "Great things never come from comfort zones.",
        "Dream it. Wish it. Do it.",
    ]
    import random
    return random.choice(quotes)


def calculator(expression: str) -> str:
    """Calculate mathematical expressions.
    
    Args:
        expression: Math expression like "2 + 2", "10 * 5", "sqrt(16)"
    """
    import math
    import re
    
    expression = expression.strip()
    if not expression:
        return "No expression provided."
    
    # Clean the expression - only allow safe characters
    # Remove any potentially dangerous characters
    allowed_pattern = r'^[0-9+\-*/().\s^%sincotalgpr]+$'
    if not re.match(allowed_pattern, expression.lower()):
        return "Invalid characters in expression. Only numbers and basic operators allowed."
    
    try:
        # Replace common math functions with math module equivalents
        safe_expression = expression.lower()
        safe_expression = safe_expression.replace('^', '**')
        safe_expression = safe_expression.replace('sqrt', 'math.sqrt')
        safe_expression = safe_expression.replace('sin', 'math.sin')
        safe_expression = safe_expression.replace('cos', 'math.cos')
        safe_expression = safe_expression.replace('tan', 'math.tan')
        safe_expression = safe_expression.replace('log', 'math.log10')
        safe_expression = safe_expression.replace('ln', 'math.log')
        safe_expression = safe_expression.replace('pi', str(math.pi))
        safe_expression = safe_expression.replace('e', str(math.e))
        
        # Evaluate the expression
        result = eval(safe_expression, {"__builtins__": {}}, {"math": math})
        
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Calculation error: {str(e)}. Make sure your expression is valid."


def flip_coin() -> str:
    """Flip a coin."""
    import random
    return random.choice(["Heads!", "Tails!"])


def roll_dice(sides: int = 6) -> str:
    """Roll a dice.
    
    Args:
        sides: Number of sides on the dice (default 6)
    """
    import random
    try:
        sides = int(sides)
        if sides < 2:
            return "Dice must have at least 2 sides."
        result = random.randint(1, sides)
        return f"Rolled a {sides}-sided dice: {result}!"
    except:
        return "Invalid number of sides. Using 6-sided dice: " + str(random.randint(1, 6))


def get_weather(city: str = "") -> str:
    """Get weather information (simplified - returns search link if no API).
    
    Args:
        city: City name for weather lookup
    """
    if city:
        encoded = requests.utils.quote(f"weather in {city}")
        return f"Weather search: https://www.google.com/search?q={encoded}"
    else:
        return "Please specify a city. Say 'weather in London' for example."


def timer(seconds: int) -> str:
    """Set a timer for specified seconds.
    
    Args:
        seconds: Number of seconds for the timer
    """
    try:
        seconds = int(seconds)
        if seconds < 1:
            return "Timer must be at least 1 second."
        
        # Start timer in background thread
        def timer_thread():
            time.sleep(seconds)
            # Try to notify
            try:
                import winsound
                winsound.Beep(1000, 1000)  # Beep for 1 second
            except:
                pass
            logger.info(f"Timer complete: {seconds} seconds")
        
        t = threading.Thread(target=timer_thread, daemon=True)
        t.start()
        
        minutes, secs = divmod(seconds, 60)
        if minutes > 0:
            return f"Timer set for {minutes} minutes and {secs} seconds."
        else:
            return f"Timer set for {seconds} seconds."
    except:
        return "Invalid time. Please specify seconds like '60' for 1 minute."


TOOL_REGISTRY = {
    "web_search": web_search,
    "plot_chart": plot_chart,
    "open_app": open_app,
    "close_app": close_app,
    "list_running_apps": list_running_apps,
    "kill_process": kill_process,
    "get_datetime": get_datetime,
    "search_youtube": search_youtube,
    "play_youtube": play_youtube,
    "play_music": play_music,
    "play_video": play_video,
    "test_keyboard": test_keyboard,
    "test_mouse": test_mouse,
    "get_joke": get_joke,
    "get_quote": get_quote,
    "calculator": calculator,
    "flip_coin": flip_coin,
    "roll_dice": roll_dice,
    "get_weather": get_weather,
    "timer": timer,
}

# Merge academic tools
try:
    from jarvis.academic_tools import (
        solve_math_problem,
        solve_physics_problem,
        plot_advanced_graph,
        solve_coordinate_geometry,
        unit_converter,
    )

    ACADEMIC_TOOL_REGISTRY = {
        "solve_math": solve_math_problem,
        "solve_physics": solve_physics_problem,
        "plot_graph": plot_advanced_graph,
        "coordinate_geometry": solve_coordinate_geometry,
        "convert_units": unit_converter,
    }
    TOOL_REGISTRY.update(ACADEMIC_TOOL_REGISTRY)
except ImportError:
    pass

# Merge document reading tools
try:
    from jarvis.document_reader import (
        read_document,
        search_documents,
        list_documents,
        get_document,
    )

    DOCUMENT_TOOL_REGISTRY = {
        "read_document": read_document,
        "search_documents": search_documents,
        "list_documents": list_documents,
        "get_document": get_document,
    }
    TOOL_REGISTRY.update(DOCUMENT_TOOL_REGISTRY)
except ImportError:
    pass

# Merge all tool registries
TOOL_REGISTRY.update(SYSTEM_CONTROL_REGISTRY)
TOOL_REGISTRY.update(DASHBOARD_REGISTRY)
TOOL_REGISTRY.update(MEMORY_REGISTRY)
TOOL_REGISTRY.update(PLUGIN_REGISTRY)

# Import and merge academic tools
try:
    from jarvis.academic_tools import ACADEMIC_REGISTRY
    TOOL_REGISTRY.update(ACADEMIC_REGISTRY)
    logger.info("✅ Academic tools loaded")
except ImportError as e:
    logger.warning(f"Academic tools not loaded: {e}")

# Import and merge learning memory tools
try:
    from jarvis.learning_memory import LEARNING_REGISTRY
    TOOL_REGISTRY.update(LEARNING_REGISTRY)
    logger.info("✅ Learning memory tools loaded")
except ImportError as e:
    logger.warning(f"Learning memory tools not loaded: {e}")
