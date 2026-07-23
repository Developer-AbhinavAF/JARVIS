"""knowledge_semantic — Knowledge base with semantic search using ChromaDB.

Provides semantic understanding and retrieval for stored knowledge.
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class SemanticKnowledgeEngine:
    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        self._chroma_available = False
        self._collection = None
        self._init_chromadb()
        
        # Fallback to JSON if ChromaDB not available
        self._fallback_file = self._data_dir / "knowledge_fallback.json"
        self._fallback_data: dict[str, Any] = {}
        self._load_fallback()

    def _init_chromadb(self) -> None:
        """Initialize ChromaDB for semantic search."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Initialize ChromaDB client
            client = chromadb.PersistentClient(
                path=str(self._data_dir / "chroma_db"),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self._collection = client.get_or_create_collection(
                name="jarvis_knowledge",
                metadata={"description": "JARVIS knowledge base"}
            )
            
            self._chroma_available = True
            logger.info("ChromaDB initialized successfully")
        except ImportError:
            logger.warning("ChromaDB not available, using fallback JSON storage")
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}, using fallback")

    def _load_fallback(self) -> None:
        """Load fallback JSON data."""
        if self._fallback_file.exists():
            try:
                self._fallback_data = json.loads(self._fallback_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to load fallback knowledge: {e}")
                self._fallback_data = {}

    def _save_fallback(self) -> bool:
        """Save fallback JSON data."""
        try:
            self._fallback_file.write_text(json.dumps(self._fallback_data, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to save fallback knowledge: {e}")
            return False

    def add_knowledge(self, content: str, source: str = "", metadata: dict[str, Any] | None = None) -> str:
        """Add knowledge entry with semantic indexing."""
        import time
        
        entry_id = f"knowledge_{int(time.time() * 1000)}"
        
        if self._chroma_available and self._collection:
            try:
                # Add to ChromaDB
                self._collection.add(
                    documents=[content],
                    metadatas=[{
                        "source": source,
                        **(metadata or {})
                    }],
                    ids=[entry_id]
                )
                logger.info(f"Added knowledge to ChromaDB: {entry_id}")
                return entry_id
            except Exception as e:
                logger.error(f"Failed to add to ChromaDB: {e}")
        
        # Fallback to JSON
        self._fallback_data[entry_id] = {
            "content": content,
            "source": source,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self._save_fallback()
        return entry_id

    def search_knowledge(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Search knowledge using semantic similarity."""
        if self._chroma_available and self._collection:
            try:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
                
                if results and results['documents'] and results['documents'][0]:
                    formatted_results = []
                    for i, doc in enumerate(results['documents'][0]):
                        formatted_results.append({
                            "content": doc,
                            "metadata": results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                            "id": results['ids'][0][i] if results['ids'] and results['ids'][0] else "",
                            "distance": results['distances'][0][i] if results['distances'] and results['distances'][0] else 0,
                        })
                    return formatted_results
            except Exception as e:
                logger.error(f"ChromaDB search failed: {e}")
        
        # Fallback to keyword search
        return self._keyword_search(query, n_results)

    def _keyword_search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Fallback keyword search in JSON storage."""
        query_lower = query.lower()
        results = []
        
        for entry_id, data in self._fallback_data.items():
            content = data.get("content", "")
            source = data.get("source", "")
            
            # Semantic similarity using word overlap as placeholder
            query_words = set(query_lower.split())
            content_words = set(content.lower().split())
            overlap = len(query_words & content_words)
            
            if overlap > 0:
                results.append({
                    "content": content,
                    "metadata": data.get("metadata", {}),
                    "id": entry_id,
                    "distance": 1.0 / (overlap + 1),  # Convert to distance
                })
        
        # Sort by distance (lower is better)
        results.sort(key=lambda x: x["distance"])
        return results[:n_results]

    def get_knowledge(self, entry_id: str) -> dict[str, Any] | None:
        """Get specific knowledge entry."""
        if self._chroma_available and self._collection:
            try:
                results = self._collection.get(ids=[entry_id])
                if results and results['documents'] and results['documents'][0]:
                    return {
                        "content": results['documents'][0][0],
                        "metadata": results['metadatas'][0][0] if results['metadatas'] and results['metadatas'][0] else {},
                        "id": entry_id,
                    }
            except Exception as e:
                logger.error(f"Failed to get from ChromaDB: {e}")
        
        # Fallback to JSON
        return self._fallback_data.get(entry_id)

    def delete_knowledge(self, entry_id: str) -> bool:
        """Delete knowledge entry."""
        if self._chroma_available and self._collection:
            try:
                self._collection.delete(ids=[entry_id])
                logger.info(f"Deleted from ChromaDB: {entry_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete from ChromaDB: {e}")
        
        # Fallback to JSON
        if entry_id in self._fallback_data:
            del self._fallback_data[entry_id]
            return self._save_fallback()
        
        return False

    def add_document_file(self, file_path: str) -> dict[str, Any]:
        """Add a document file to knowledge base."""
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        try:
            content = path.read_text(encoding="utf-8")
            entry_id = self.add_knowledge(
                content=content,
                source=str(path),
                metadata={"file_type": path.suffix, "file_name": path.name}
            )
            return {"success": True, "entry_id": entry_id, "file": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stats(self) -> dict[str, Any]:
        """Get knowledge base statistics."""
        count = 0
        if self._chroma_available and self._collection:
            try:
                count = self._collection.count()
            except Exception as e:
                logger.error(f"Failed to get ChromaDB count: {e}")
        
        if count == 0:
            count = len(self._fallback_data)
        
        return {
            "total_entries": count,
            "chroma_available": self._chroma_available,
            "data_dir": str(self._data_dir),
        }


# Singleton instance
semantic_knowledge = SemanticKnowledgeEngine()
