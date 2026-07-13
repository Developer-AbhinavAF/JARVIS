from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from jarvis.router_service import router_client
from jarvis.memory_manager import intelligent_memory

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeUnit:
    topic: str
    concepts: list[str]
    keywords: list[str]
    summary: str
    source_link: str
    source_type: str
    created_at: str


class KnowledgeIngestionService:
    def ingest_source(self, source: str, *, source_type: str | None = None) -> KnowledgeUnit:
        source_type = source_type or self._detect_source_type(source)
        text = self._extract_text(source, source_type)
        unit = self._generate_knowledge_unit(text, source, source_type)
        self._store(unit, text)
        return unit

    def _detect_source_type(self, source: str) -> str:
        lowered = source.lower()
        if "youtube.com/watch" in lowered or "youtu.be/" in lowered:
            return "youtube"
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return "url"
        if lowered.endswith(".pdf") or Path(source).suffix.lower() == ".pdf":
            return "pdf"
        return "note"

    def _extract_text(self, source: str, source_type: str) -> str:
        if source_type == "url":
            return self._extract_url_text(source)
        if source_type == "youtube":
            return self._extract_youtube_text(source)
        if source_type == "pdf":
            return self._extract_pdf_text(source)
        return source

    def _extract_url_text(self, url: str) -> str:
        response = requests.get(url, timeout=20, headers={"User-Agent": "JARVIS/2.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text)

    def _extract_youtube_text(self, url: str) -> str:
        video_id = self._youtube_id(url)
        if not video_id:
            return f"YouTube URL: {url}"
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join(item.get("text", "") for item in transcript)
        except Exception as exc:
            logger.warning("YouTube transcript unavailable: %s", exc)
            return f"YouTube URL: {url}"

    def _youtube_id(self, url: str) -> str | None:
        match = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]+)", url)
        return match.group(1) if match else None

    def _extract_pdf_text(self, source: str) -> str:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(source)
        try:
            import PyPDF2
            with path.open("rb") as handle:
                reader = PyPDF2.PdfReader(handle)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise RuntimeError(f"Failed to extract PDF text: {exc}") from exc

    def _generate_knowledge_unit(self, text: str, source: str, source_type: str) -> KnowledgeUnit:
        compact = re.sub(r"\s+", " ", text).strip()
        if len(compact) > 12000:
            compact = compact[:12000]

        prompt = f"""Create a compact JSON knowledge unit from this source.
Return keys: topic, concepts, keywords, summary.
Source: {source}
Text:
{compact}
"""
        try:
            raw = router_client.chat(
                [
                    {"role": "system", "content": "Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=700,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            data = json.loads(raw if isinstance(raw, str) else "".join(raw))
        except Exception as exc:
            logger.warning("Knowledge summarization fallback used: %s", exc)
            data = self._fallback_unit(compact)

        return KnowledgeUnit(
            topic=str(data.get("topic") or "General Knowledge"),
            concepts=[str(item) for item in data.get("concepts", [])][:12],
            keywords=[str(item) for item in data.get("keywords", [])][:16],
            summary=str(data.get("summary") or compact[:500]),
            source_link=source,
            source_type=source_type,
            created_at=datetime.now().isoformat(),
        )

    def _fallback_unit(self, text: str) -> dict[str, Any]:
        words = [word.strip(".,;:!?()[]{}").lower() for word in text.split()]
        keywords = []
        for word in words:
            if len(word) > 5 and word not in keywords:
                keywords.append(word)
            if len(keywords) >= 10:
                break
        return {
            "topic": "Imported Knowledge",
            "concepts": keywords[:6],
            "keywords": keywords,
            "summary": text[:700],
        }

    def _store(self, unit: KnowledgeUnit, full_text: str) -> None:
        content = json.dumps(
            {
                **asdict(unit),
                "full_text_preview": full_text[:4000],
            },
            ensure_ascii=True,
        )
        intelligent_memory.remember(
            content,
            category="educational_content",
            source=unit.source_link,
            importance_score=0.82,
            explicit=True,
            summary=f"{unit.topic}: {unit.summary}",
        )

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return intelligent_memory.search(query, limit=limit, category="educational_content")


knowledge_ingestion = KnowledgeIngestionService()
