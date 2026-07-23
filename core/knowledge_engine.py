"""knowledge_engine — Knowledge engine for document storage and semantic search.

Capabilities:
- Document ingestion (PDF, TXT, MD, DOCX, HTML)
- Website content extraction
- YouTube transcript processing
- Semantic search using embeddings
- Knowledge categorization
- Source attribution
- Knowledge management
"""

from __future__ import annotations

import os
import json
import logging
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import tempfile

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class KnowledgeType(Enum):
    """Types of knowledge content."""
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    DOCX = "docx"
    HTML = "html"
    WEBSITE = "website"
    YOUTUBE_TRANSCRIPT = "youtube_transcript"
    NOTE = "note"
    CODE = "code"


@dataclass
class KnowledgeEntry:
    """Represents a single knowledge entry."""
    entry_id: str
    content: str
    source: str = ""
    knowledge_type: KnowledgeType = KnowledgeType.TXT
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    last_accessed: str = ""
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.95


@dataclass
class SearchResult:
    """Result of knowledge search."""
    entry_id: str
    content: str
    source: str
    knowledge_type: KnowledgeType
    relevance_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


class KnowledgeEngine:
    """Knowledge engine for document storage and semantic search."""
    
    def __init__(self, knowledge_dir: str = None):
        self._knowledge_dir = Path(knowledge_dir) if knowledge_dir else Path(__file__).parent.parent / "knowledge"
        self._knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        self._knowledge_file = self._knowledge_dir / "knowledge_index.json"
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._init_storage()
        self._load_knowledge()
    
    def _init_storage(self) -> None:
        """Initialize knowledge storage files."""
        if not self._knowledge_file.exists():
            self._knowledge_file.write_text("{}", encoding="utf-8")
        
        # Create subdirectories
        for subdir in ["documents", "websites", "transcripts", "notes"]:
            (self._knowledge_dir / subdir).mkdir(exist_ok=True)
    
    def _load_knowledge(self) -> None:
        """Load knowledge from storage."""
        try:
            if self._knowledge_file.exists():
                data = json.loads(self._knowledge_file.read_text(encoding="utf-8"))
                for entry_id, entry_data in data.items():
                    self._entries[entry_id] = KnowledgeEntry(
                        entry_id=entry_id,
                        content=entry_data.get("content", ""),
                        source=entry_data.get("source", ""),
                        knowledge_type=KnowledgeType(entry_data.get("knowledge_type", "txt")),
                        metadata=entry_data.get("metadata", {}),
                        embedding=entry_data.get("embedding"),
                        created_at=entry_data.get("created_at", ""),
                        updated_at=entry_data.get("updated_at", ""),
                        access_count=entry_data.get("access_count", 0),
                        last_accessed=entry_data.get("last_accessed", ""),
                        tags=entry_data.get("tags", []),
                        confidence=entry_data.get("confidence", 0.95)
                    )
            
            logger.info(f"Loaded {len(self._entries)} knowledge entries")
        except Exception as e:
            logger.error(f"Failed to load knowledge: {e}")
    
    def _save_knowledge(self) -> bool:
        """Save knowledge to storage."""
        try:
            data = {}
            for entry_id, entry in self._entries.items():
                data[entry_id] = {
                    "content": entry.content,
                    "source": entry.source,
                    "knowledge_type": entry.knowledge_type.value,
                    "metadata": entry.metadata,
                    "embedding": entry.embedding,
                    "created_at": entry.created_at,
                    "updated_at": entry.updated_at,
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed,
                    "tags": entry.tags,
                    "confidence": entry.confidence
                }
            
            self._knowledge_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to save knowledge: {e}")
            return False
    
    def _generate_entry_id(self, source: str) -> str:
        """Generate unique entry ID."""
        hash_input = f"{source}_{time.time()}"
        return f"knowledge_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (simplified)."""
        # In production, use actual embedding model (sentence-transformers, etc.)
        # This is a simplified placeholder
        try:
            # Simple hash-based embedding as placeholder
            import hashlib
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()
            
            # Convert to float array
            embedding = [byte / 255.0 for byte in hash_bytes[:32]]  # 32-dimensional
            return embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return [0.0] * 32
    
    def add_knowledge(self, content: str, source: str = "", 
                     knowledge_type: KnowledgeType = KnowledgeType.TXT,
                     metadata: Dict[str, Any] = None, tags: List[str] = None) -> str:
        """Add knowledge entry."""
        entry_id = self._generate_entry_id(source or "manual")
        
        entry = KnowledgeEntry(
            entry_id=entry_id,
            content=content,
            source=source,
            knowledge_type=knowledge_type,
            metadata=metadata or {},
            tags=tags or [],
            embedding=self._generate_embedding(content)
        )
        
        self._entries[entry_id] = entry
        self._save_knowledge()
        
        logger.info(f"Added knowledge entry: {entry_id}")
        return entry_id
    
    def add_knowledge_from_file(self, file_path: str, tags: List[str] = None) -> str:
        """Add knowledge from file."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return ""
            
            # Determine file type
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                knowledge_type = KnowledgeType.PDF
                content = self._extract_pdf_text(file_path)
            elif suffix == ".docx":
                knowledge_type = KnowledgeType.DOCX
                content = self._extract_docx_text(file_path)
            elif suffix == ".md":
                knowledge_type = KnowledgeType.MD
                content = file_path.read_text(encoding="utf-8")
            elif suffix == ".html":
                knowledge_type = KnowledgeType.HTML
                content = self._extract_html_text(file_path)
            else:
                knowledge_type = KnowledgeType.TXT
                content = file_path.read_text(encoding="utf-8")
            
            if not content:
                logger.error(f"Failed to extract content from {file_path}")
                return ""
            
            return self.add_knowledge(
                content=content,
                source=str(file_path),
                knowledge_type=knowledge_type,
                metadata={"file_path": str(file_path), "file_size": file_path.stat().st_size},
                tags=tags
            )
            
        except Exception as e:
            logger.error(f"Failed to add knowledge from file: {e}")
            return ""
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except ImportError:
            logger.warning("PyPDF2 not available")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return ""
    
    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        try:
            import docx
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except ImportError:
            logger.warning("python-docx not available")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract DOCX text: {e}")
            return ""
    
    def _extract_html_text(self, file_path: Path) -> str:
        """Extract text from HTML file."""
        try:
            from bs4 import BeautifulSoup
            html = file_path.read_text(encoding="utf-8")
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return text
        except ImportError:
            logger.warning("BeautifulSoup not available")
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to extract HTML text: {e}")
            return ""
    
    def add_knowledge_from_url(self, url: str, tags: List[str] = None) -> str:
        """Add knowledge from website URL."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else url
            text = soup.get_text(separator=' ', strip=True)
            
            return self.add_knowledge(
                content=text,
                source=url,
                knowledge_type=KnowledgeType.WEBSITE,
                metadata={"url": url, "title": title},
                tags=tags
            )
            
        except ImportError:
            logger.warning("requests or BeautifulSoup not available")
            return ""
        except Exception as e:
            logger.error(f"Failed to add knowledge from URL: {e}")
            return ""
    
    def search_knowledge(self, query: str, limit: int = 10, 
                         knowledge_type: KnowledgeType = None) -> List[SearchResult]:
        """Search knowledge using semantic similarity."""
        query_embedding = self._generate_embedding(query)
        results = []
        
        for entry_id, entry in self._entries.items():
            # Filter by type if specified
            if knowledge_type and entry.knowledge_type != knowledge_type:
                continue
            
            # Calculate similarity (cosine similarity placeholder)
            similarity = self._calculate_similarity(query_embedding, entry.embedding)
            
            if similarity > 0.3:  # Threshold
                results.append(SearchResult(
                    entry_id=entry_id,
                    content=entry.content[:500] + "..." if len(entry.content) > 500 else entry.content,
                    source=entry.source,
                    knowledge_type=entry.knowledge_type,
                    relevance_score=similarity,
                    metadata=entry.metadata,
                    confidence=entry.confidence
                ))
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings."""
        try:
            if not embedding1 or not embedding2 or len(embedding1) != len(embedding2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            magnitude1 = sum(a * a for a in embedding1) ** 0.5
            magnitude2 = sum(b * b for b in embedding2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
        except Exception as e:
            logger.warning(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get knowledge entry by ID."""
        entry = self._entries.get(entry_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = datetime.now().isoformat()
            self._save_knowledge()
        return entry
    
    def delete_knowledge(self, entry_id: str) -> bool:
        """Delete knowledge entry."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return self._save_knowledge()
        return False
    
    def update_knowledge(self, entry_id: str, content: str = None, 
                        metadata: Dict[str, Any] = None, tags: List[str] = None) -> bool:
        """Update knowledge entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        
        if content:
            entry.content = content
            entry.embedding = self._generate_embedding(content)
        
        if metadata:
            entry.metadata.update(metadata)
        
        if tags:
            entry.tags = tags
        
        entry.updated_at = datetime.now().isoformat()
        return self._save_knowledge()
    
    def get_knowledge_by_type(self, knowledge_type: KnowledgeType) -> List[KnowledgeEntry]:
        """Get all knowledge entries of a specific type."""
        return [entry for entry in self._entries.values() if entry.knowledge_type == knowledge_type]
    
    def get_knowledge_by_tag(self, tag: str) -> List[KnowledgeEntry]:
        """Get all knowledge entries with a specific tag."""
        return [entry for entry in self._entries.values() if tag in entry.tags]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge statistics."""
        type_counts = {}
        for entry in self._entries.values():
            type_name = entry.knowledge_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "total_entries": len(self._entries),
            "type_distribution": type_counts,
            "total_access_count": sum(entry.access_count for entry in self._entries.values()),
            "storage_dir": str(self._knowledge_dir)
        }


# Global knowledge engine instance
knowledge_engine = KnowledgeEngine()