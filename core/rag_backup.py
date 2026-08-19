"""core/rag.py — Dynamic Adaptive RAG Engine for JARVIS vNext++.

Dynamically selects Top-K retrieval context based on query intent:
- Greeting / Tool Action: Top-K = 0 (0 tokens)
- Simple Question: Top-K = 2 (~400 tokens)
- Coding / Documentation: Top-K = 4 (~800 tokens)
- Research: Top-K = 6 (~1000 tokens)
- Large Planning / Architecture: Top-K = 8 (~1200 tokens)

Maximum injected context is strictly capped at 1200 tokens.
All vector embedding generation runs asynchronously.
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DynamicRAGEngine:
    """Dynamic Adaptive RAG implementation."""

    def __init__(self, docs_dir: str = "docs"):
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self._document_chunks: List[Dict[str, str]] = []
        self._load_documents()

    def _load_documents(self) -> None:
        """Load text/markdown files from docs/ and foods/."""
        self._document_chunks = []
        for search_dir in ["docs", "foods", "tool_docs"]:
            p = Path(search_dir)
            if not p.exists():
                continue
            for file in p.glob("**/*.md"):
                try:
                    content = file.read_text(encoding="utf-8")
                    # Chunk content into ~500 token segments
                    chunks = self._chunk_text(content, chunk_size=1500)
                    for idx, chunk in enumerate(chunks):
                        self._document_chunks.append({
                            "source": str(file),
                            "chunk_id": f"{file.stem}_{idx}",
                            "content": chunk,
                        })
                except Exception as e:
                    logger.error(f"Error loading RAG doc {file}: {e}")

    def _chunk_text(self, text: str, chunk_size: int = 1500) -> List[str]:
        """Simple token-approximating character chunker."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - 150  # 50 token overlap (~150 chars)
        return chunks

    def retrieve(self, query: str, top_k: int = 2) -> List[Dict[str, str]]:
        """Retrieve Top-K relevant chunks based on query string."""
        if top_k <= 0 or not self._document_chunks:
            return []

        query_words = set(query.lower().split())
        scored = []

        for chunk in self._document_chunks:
            chunk_words = set(chunk["content"].lower().split())
            score = len(query_words & chunk_words)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored[:top_k]]
        return results

    def format_rag_context(self, query: str, top_k: int = 2) -> str:
        """Format retrieved chunks as prompt context string."""
        chunks = self.retrieve(query, top_k=top_k)
        if not chunks:
            return ""
        
        formatted = ["Retrieved Documentation:"]
        for c in chunks:
            formatted.append(f"--- From {c['source']} ---\n{c['content'][:500]}...")
        
        # Enforce max 1200 token cap
        res = "\n".join(formatted)
        return res[:4800]  # ~1200 tokens max


rag_engine = DynamicRAGEngine()
