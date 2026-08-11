"""tools_nasa — NASA APOD & Image/Video Library integration for JARVIS.

Provides:
- NASA Astronomy Picture of the Day (APOD)
- NASA Image and Video Library search
- Normalized result format for frontend rendering
"""

from __future__ import annotations

import os
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

NASA_API_KEY = os.getenv("NASA_API_KEY", "5X38YprHlj9n18oxeYSbEk2wYwgNei5tnDX5NOsD")
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
NASA_IMAGES_URL = "https://images-api.nasa.gov"


@dataclass
class NasaResult:
    success: bool = False
    source: str = "NASA"
    query: str = ""
    results: List[Dict[str, Any]] = None
    error: str = ""

    def __post_init__(self):
        if self.results is None:
            self.results = []


def _fetch_apod(date: str = None, count: int = 1) -> NasaResult:
    """Fetch NASA Astronomy Picture of the Day."""
    params: Dict[str, Any] = {"api_key": NASA_API_KEY}
    if date:
        params["date"] = date
    if count > 1:
        params["count"] = count

    try:
        resp = httpx.get(NASA_APOD_URL, params=params, timeout=15.0)
        if resp.status_code != 200:
            return NasaResult(success=False, error=f"NASA API returned {resp.status_code}")

        data = resp.json()
        items = data if isinstance(data, list) else [data]
        results = []

        for item in items:
            media_type = item.get("media_type", "image")
            image_url = item.get("hdurl") or item.get("url") or ""
            thumb_url = item.get("thumbnail_url") or image_url

            results.append({
                "title": item.get("title", "Untitled"),
                "description": item.get("explanation", ""),
                "media_type": media_type,
                "image_url": image_url,
                "thumbnail_url": thumb_url,
                "source_url": item.get("url", ""),
                "date": item.get("date", ""),
                "copyright": item.get("copyright", ""),
                "nasa_id": f"apod_{item.get('date', 'unknown')}",
            })

        return NasaResult(
            success=True,
            source="NASA_APOD",
            query="Astronomy Picture of the Day",
            results=results,
        )
    except Exception as e:
        logger.error("NASA APOD error: %s", e)
        return NasaResult(success=False, error=str(e))


def _fetch_nasa_images(query: str, media_type: str = "image", page: int = 1, page_size: int = 6) -> NasaResult:
    """Search NASA Image and Video Library."""
    search_url = f"{NASA_IMAGES_URL}/search"
    params: Dict[str, Any] = {
        "q": query,
        "media_type": media_type,
        "page": page,
        "page_size": page_size,
    }

    try:
        resp = httpx.get(search_url, params=params, timeout=15.0)
        if resp.status_code != 200:
            return NasaResult(success=False, query=query, error=f"NASA Images API returned {resp.status_code}")

        data = resp.json()
        items = data.get("collection", {}).get("items", [])
        results = []

        for item in items:
            item_data = item.get("data", [{}])
            if not item_data:
                continue
            meta = item_data[0] if isinstance(item_data, list) else item_data

            links = item.get("links", [])
            thumb_url = ""
            image_url = ""
            source_url = ""
            for link in links:
                if link.get("rel") == "preview":
                    thumb_url = link.get("href", "")
                if link.get("rel") == "canonical":
                    image_url = link.get("href", "")
                    source_url = link.get("href", "")

            nasa_id = meta.get("nasa_id", "")
            if not image_url and nasa_id:
                image_url = f"https://images-assets.nasa.gov/image/{nasa_id}/{nasa_id}~orig.jpg"
            if not thumb_url and nasa_id:
                thumb_url = f"https://images-assets.nasa.gov/image/{nasa_id}/{nasa_id}~medium.jpg"

            description = meta.get("description", "")
            if len(description) > 300:
                description = description[:300] + "..."

            results.append({
                "title": meta.get("title", "Untitled"),
                "description": description,
                "media_type": meta.get("media_type", "image"),
                "image_url": image_url,
                "thumbnail_url": thumb_url,
                "source_url": source_url or meta.get("href", ""),
                "nasa_id": nasa_id,
                "date": meta.get("date_created", ""),
                "center": meta.get("center", ""),
            })

        return NasaResult(
            success=True,
            source="NASA_IMAGES",
            query=query,
            results=results,
        )
    except Exception as e:
        logger.error("NASA Images search error for '%s': %s", query, e)
        return NasaResult(success=False, query=query, error=str(e))


def _fetch_nasa_asset(nasa_id: str) -> NasaResult:
    """Fetch metadata for a specific NASA asset."""
    url = f"{NASA_IMAGES_URL}/asset/{nasa_id}"
    try:
        resp = httpx.get(url, timeout=15.0)
        if resp.status_code != 200:
            return NasaResult(success=False, error=f"NASA Asset API returned {resp.status_code}")

        data = resp.json()
        collection = data.get("collection", {})
        items = collection.get("items", [])

        results = []
        for item in items:
            href = item.get("href", "")
            if href.lower().endswith((".jpg", ".png", ".jpeg", ".gif")):
                results.append({
                    "nasa_id": nasa_id,
                    "image_url": href,
                    "thumbnail_url": href,
                    "title": nasa_id,
                })
                break

        return NasaResult(
            success=True,
            source="NASA_ASSET",
            query=nasa_id,
            results=results,
        )
    except Exception as e:
        logger.error("NASA Asset error for '%s': %s", nasa_id, e)
        return NasaResult(success=False, error=str(e))


# ── Public API used by tool_registry ──────────────────────────────────

def nasa_apod(date: str = "") -> Dict[str, Any]:
    """Get NASA Astronomy Picture of the Day.

    Args:
        date: Optional date string (YYYY-MM-DD). Empty = today.
    """
    result = _fetch_apod(date=date if date else None)
    return {
        "success": result.success,
        "output": result.results[0] if result.results else result.error,
        "results": result.results,
        "source": result.source,
        "error": result.error,
    }


def nasa_image_search(query: str = "", media_type: str = "image", page: int = 1, page_size: int = 6) -> Dict[str, Any]:
    """Search NASA Image and Video Library.

    Args:
        query: Search query (e.g. "black holes", "Mars", "James Webb").
        media_type: "image", "video", or "audio".
        page: Page number (1-indexed).
        page_size: Results per page (max 100).
    """
    if not query:
        return {"success": False, "error": "No search query provided", "results": []}
    result = _fetch_nasa_images(query, media_type=media_type, page=page, page_size=page_size)
    return {
        "success": result.success,
        "output": f"Found {len(result.results)} NASA {media_type}s for '{query}'" if result.success else result.error,
        "results": result.results,
        "source": result.source,
        "query": query,
        "count": len(result.results),
        "error": result.error,
    }


def nasa_asset_lookup(nasa_id: str = "") -> Dict[str, Any]:
    """Look up a specific NASA asset by ID."""
    if not nasa_id:
        return {"success": False, "error": "No NASA ID provided", "results": []}
    result = _fetch_nasa_asset(nasa_id)
    return {
        "success": result.success,
        "output": result.results[0] if result.results else result.error,
        "results": result.results,
        "source": result.source,
        "error": result.error,
    }
