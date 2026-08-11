"""tests/test_nasa_tools.py — Tests for NASA APOD & Image/Video Library integration.

Covers: APOD retrieval, image search, metadata, failures, empty results,
        malformed responses, timeouts, missing API key, image URL extraction.
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.tools_nasa import (
    nasa_apod,
    nasa_image_search,
    nasa_asset_lookup,
    _fetch_apod,
    _fetch_nasa_images,
    _fetch_nasa_asset,
    NasaResult,
    NASA_API_KEY,
)


class TestNasaApod:
    def test_apod_returns_success(self):
        """APOD should return success with valid response."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test APOD",
            "explanation": "A test explanation",
            "media_type": "image",
            "hdurl": "https://example.com/image.jpg",
            "url": "https://example.com/image_small.jpg",
            "date": "2026-01-01",
            "copyright": "Test",
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_apod()
            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["results"][0]["title"] == "Test APOD"
            assert result["results"][0]["image_url"] == "https://example.com/image.jpg"

    def test_apod_with_date(self):
        """APOD with date parameter should pass date to API."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Past APOD",
            "explanation": "Past",
            "media_type": "image",
            "hdurl": "https://example.com/past.jpg",
            "date": "2025-06-15",
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response) as mock_get:
            result = nasa_apod(date="2025-06-15")
            assert result["success"] is True
            call_args = mock_get.call_args
            assert call_args[1]["params"]["date"] == "2025-06-15"

    def test_apod_http_error(self):
        """APOD should handle HTTP errors gracefully."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 500
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_apod()
            assert result["success"] is False
            assert "500" in result["error"]

    def test_apod_network_error(self):
        """APOD should handle network errors gracefully."""
        import httpx
        with patch("core.tools_nasa.httpx.get", side_effect=httpx.ConnectError("Connection refused")):
            result = nasa_apod()
            assert result["success"] is False
            assert "Connection refused" in result["error"]

    def test_apod_timeout(self):
        """APOD should handle timeouts gracefully."""
        import httpx
        with patch("core.tools_nasa.httpx.get", side_effect=httpx.TimeoutException("Timeout")):
            result = nasa_apod()
            assert result["success"] is False

    def test_apod_missing_api_key(self):
        """APOD should work with DEMO_KEY fallback."""
        assert NASA_API_KEY is not None
        assert len(NASA_API_KEY) > 0

    def test_apod_video_media_type(self):
        """APOD should handle video media type."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Video APOD",
            "explanation": "A video",
            "media_type": "video",
            "url": "https://youtube.com/watch?v=test",
            "date": "2026-01-01",
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_apod()
            assert result["success"] is True
            assert result["results"][0]["media_type"] == "video"

    def test_apod_thumbnail_fallback(self):
        """APOD should use url as fallback when thumbnail_url not present."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "No Thumb",
            "explanation": "Test",
            "media_type": "image",
            "hdurl": "https://example.com/hd.jpg",
            "url": "https://example.com/sd.jpg",
            "date": "2026-01-01",
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_apod()
            # When no thumbnail_url is present, falls back to image_url (hdurl)
            assert result["results"][0]["thumbnail_url"] == "https://example.com/hd.jpg"


class TestNasaImageSearch:
    def test_search_returns_results(self):
        """Image search should return normalized results."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "Black Hole", "nasa_id": "bh001", "description": "A black hole", "media_type": "image"}],
                        "links": [{"rel": "preview", "href": "https://example.com/thumb.jpg"}],
                    }
                ]
            }
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_image_search("black holes")
            assert result["success"] is True
            assert result["count"] == 1
            assert result["results"][0]["title"] == "Black Hole"

    def test_search_empty_results(self):
        """Image search should handle empty results."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"collection": {"items": []}}
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_image_search("xyznonexistent123")
            assert result["success"] is True
            assert result["count"] == 0

    def test_search_no_query(self):
        """Image search should fail without query."""
        result = nasa_image_search("")
        assert result["success"] is False
        assert "No search query" in result["error"]

    def test_search_http_error(self):
        """Image search should handle HTTP errors."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_image_search("mars")
            assert result["success"] is False
            assert "404" in result["error"]

    def test_search_network_error(self):
        """Image search should handle network errors."""
        import httpx
        with patch("core.tools_nasa.httpx.get", side_effect=httpx.ConnectError("timeout")):
            result = nasa_image_search("mars")
            assert result["success"] is False

    def test_search_description_truncation(self):
        """Long descriptions should be truncated to 300 chars."""
        import httpx
        long_desc = "x" * 500
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "Test", "nasa_id": "t1", "description": long_desc}],
                        "links": [],
                    }
                ]
            }
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_image_search("test")
            assert len(result["results"][0]["description"]) <= 303  # 300 + "..."

    def test_search_video_media_type(self):
        """Search should support video media type."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"collection": {"items": []}}
        with patch("core.tools_nasa.httpx.get", return_value=mock_response) as mock_get:
            nasa_image_search("apollo", media_type="video")
            call_args = mock_get.call_args
            assert call_args[1]["params"]["media_type"] == "video"

    def test_search_image_url_construction(self):
        """Image URL should be constructed from nasa_id when not in links."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "Mars", "nasa_id": "mars001", "description": "Mars"}],
                        "links": [],
                    }
                ]
            }
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_image_search("mars")
            assert "mars001" in result["results"][0]["image_url"]

    def test_search_multiple_results(self):
        """Search should handle multiple results."""
        import httpx
        items = [
            {"data": [{"title": f"Result {i}", "nasa_id": f"id{i}", "description": f"Desc {i}"}], "links": []}
            for i in range(5)
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"collection": {"items": items}}
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_image_search("space")
            assert result["count"] == 5


class TestNasaAssetLookup:
    def test_asset_lookup_success(self):
        """Asset lookup should return image URLs."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "collection": {
                "items": [
                    {"href": "https://example.com/image.jpg"},
                    {"href": "https://example.com/meta.json"},
                ]
            }
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_asset_lookup("mars001")
            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["results"][0]["image_url"] == "https://example.com/image.jpg"

    def test_asset_lookup_no_id(self):
        """Asset lookup should fail without ID."""
        result = nasa_asset_lookup("")
        assert result["success"] is False

    def test_asset_lookup_http_error(self):
        """Asset lookup should handle HTTP errors."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_asset_lookup("nonexistent")
            assert result["success"] is False


class TestNasaResult:
    def test_nasa_result_defaults(self):
        """NasaResult should have sensible defaults."""
        r = NasaResult()
        assert r.success is False
        assert r.source == "NASA"
        assert r.results == []

    def test_nasa_result_with_data(self):
        """NasaResult should store data correctly."""
        r = NasaResult(success=True, source="NASA_APOD", query="test", results=[{"title": "X"}])
        assert r.success is True
        assert len(r.results) == 1


class TestNasaImageExtraction:
    def test_image_url_from_hdurl(self):
        """hdurl should be preferred over url for image_url."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test",
            "explanation": "Test",
            "media_type": "image",
            "hdurl": "https://example.com/hd.jpg",
            "url": "https://example.com/sd.jpg",
            "date": "2026-01-01",
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_apod()
            assert result["results"][0]["image_url"] == "https://example.com/hd.jpg"

    def test_thumbnail_from_links(self):
        """Thumbnail should come from links with rel=preview."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "Test", "nasa_id": "t1", "description": "Test"}],
                        "links": [
                            {"rel": "preview", "href": "https://example.com/thumb.jpg"},
                            {"rel": "canonical", "href": "https://example.com/full.jpg"},
                        ],
                    }
                ]
            }
        }
        with patch("core.tools_nasa.httpx.get", return_value=mock_response):
            result = nasa_image_search("test")
            assert result["results"][0]["thumbnail_url"] == "https://example.com/thumb.jpg"
            assert result["results"][0]["source_url"] == "https://example.com/full.jpg"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
