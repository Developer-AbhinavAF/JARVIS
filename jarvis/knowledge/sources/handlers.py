"""Source Handlers — Process specific knowledge sources into the pipeline."""

from __future__ import annotations

import re
import logging
from typing import Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SourceResult:
    """Result from processing a source."""
    source: str = ""
    source_type: str = ""
    title: str = ""
    content: str = ""
    chunks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str = ""


class DocumentHandler:
    """Process documents: PDF, DOCX, TXT, Markdown."""

    def process(self, path: str) -> SourceResult:
        result = SourceResult(source=path, source_type="document")
        try:
            ext = path.rsplit(".", 1)[-1].lower() if "." in path else "txt"
            if ext == "txt" or ext == "md":
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    result.content = f.read()
                result.title = path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
            elif ext == "pdf":
                result = self._process_pdf(path, result)
            elif ext in ("docx", "doc"):
                result = self._process_docx(path, result)
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    result.content = f.read()
                result.title = path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]

            if result.content:
                result.chunks = self._chunk(result.content)
        except Exception as e:
            result.success = False
            result.error = str(e)
        return result

    def _process_pdf(self, path: str, result: SourceResult) -> SourceResult:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            result.content = "\n\n".join(text_parts)
            result.title = path.rsplit("\\", 1)[-1]
            result.metadata["pages"] = len(reader.pages)
        except ImportError:
            result.success = False
            result.error = "PyPDF2 not installed"
        except Exception as e:
            result.success = False
            result.error = str(e)
        return result

    def _process_docx(self, path: str, result: SourceResult) -> SourceResult:
        try:
            import docx
            doc = docx.Document(path)
            result.content = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
            result.title = path.rsplit("\\", 1)[-1]
        except ImportError:
            result.success = False
            result.error = "python-docx not installed"
        except Exception as e:
            result.success = False
            result.error = str(e)
        return result

    def _chunk(self, text: str, max_size: int = 1000) -> list[str]:
        if len(text) <= max_size:
            return [text] if text else []
        chunks: list[str] = []
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > max_size:
                if current:
                    chunks.append(current)
                current = para
            else:
                current = f"{current}\n\n{para}" if current else para
        if current:
            chunks.append(current)
        return chunks


class YouTubeHandler:
    """Process YouTube video transcripts."""

    def process(self, url: str) -> SourceResult:
        result = SourceResult(source=url, source_type="youtube")
        try:
            video_id = self._extract_video_id(url)
            if video_id:
                result.metadata["video_id"] = video_id
                result.title = f"YouTube Video {video_id}"
                result.content = f"YouTube video: {url}"
                result.chunks = [result.content]
        except Exception as e:
            result.success = False
            result.error = str(e)
        return result

    def _extract_video_id(self, url: str) -> str | None:
        patterns = [
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


class GitHubHandler:
    """Process GitHub repositories."""

    def process(self, url: str) -> SourceResult:
        result = SourceResult(source=url, source_type="github")
        try:
            repo_info = self._parse_repo_url(url)
            if repo_info:
                result.metadata["owner"] = repo_info["owner"]
                result.metadata["repo"] = repo_info["repo"]
                result.title = f"{repo_info['owner']}/{repo_info['repo']}"
                result.content = f"GitHub repository: {result.title}"
                result.chunks = [result.content]
        except Exception as e:
            result.success = False
            result.error = str(e)
        return result

    def _parse_repo_url(self, url: str) -> dict | None:
        match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
        if match:
            return {"owner": match.group(1), "repo": match.group(2)}
        return None


class WebsiteHandler:
    """Process website content."""

    def process(self, url: str, content: str = "") -> SourceResult:
        result = SourceResult(source=url, source_type="website")
        try:
            if content:
                result.content = self._clean_html(content)
                result.title = self._extract_title(content) or url
            else:
                result.content = f"Website: {url}"
                result.title = url
            result.chunks = [result.content] if result.content else []
        except Exception as e:
            result.success = False
            result.error = str(e)
        return result

    def _clean_html(self, html: str) -> str:
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_title(self, html: str) -> str:
        match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        return match.group(1).strip() if match else ""


# Global instances
document_handler = DocumentHandler()
youtube_handler = YouTubeHandler()
github_handler = GitHubHandler()
website_handler = WebsiteHandler()

__all__ = [
    "DocumentHandler", "YouTubeHandler", "GitHubHandler", "WebsiteHandler",
    "SourceResult", "document_handler", "youtube_handler", "github_handler", "website_handler",
]
