"""core/web_food_loader.py — /web_food directory loader with change detection.

This module implements:
- Automatic discovery of .md files in /web_food
- File fingerprinting for change detection
- Hot reload when files change
- Indexed/searchable content
- No blind injection of entire directory

Architecture:
    /web_food/**/*.md
        ↓
    Discovery & Fingerprinting
        ↓
    Load & Parse
        ↓
    Index & Cache
        ↓
    Change Detection
        ↓
    Selective Reload
"""

from __future__ import annotations

import os
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class WebFoodDocument:
    """Represents a single /web_food document."""
    path: str
    content: str
    hash: str
    modified_at: float
    size: int
    indexed_at: float
    category: str = ""
    tags: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "content": self.content,
            "hash": self.hash,
            "modified_at": self.modified_at,
            "size": self.size,
            "indexed_at": self.indexed_at,
            "category": self.category,
            "tags": list(self.tags),
        }


@dataclass
class WebFoodChange:
    """Represents a detected change in /web_food."""
    change_type: str  # "added", "modified", "deleted", "renamed"
    path: str
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    detected_at: float = field(default_factory=time.time)


class WebFoodLoader:
    """Loader for /web_food directory with change detection and hot reload."""
    
    def __init__(self, web_food_dir: str = "web_food"):
        self.web_food_dir = Path(web_food_dir)
        self.web_food_dir.mkdir(parents=True, exist_ok=True)
        
        # Document registry: path -> WebFoodDocument
        self._documents: Dict[str, WebFoodDocument] = {}
        
        # Fingerprint registry: path -> hash
        self._fingerprints: Dict[str, str] = {}
        
        # Category index: category -> List[WebFoodDocument]
        self._category_index: Dict[str, List[WebFoodDocument]] = {}
        
        # Tag index: tag -> List[WebFoodDocument]
        self._tag_index: Dict[str, List[WebFoodDocument]] = {}
        
        # Change history
        self._change_history: List[WebFoodChange] = []
        
        # Statistics
        self._stats = {
            "total_documents": 0,
            "total_size_bytes": 0,
            "last_load_time": 0.0,
            "last_change_detection_time": 0.0,
            "total_changes_detected": 0,
        }
        
        # Initial load
        self._load_all()
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error("Error calculating hash for %s: %s", file_path, e)
            return ""
    
    def _discover_markdown_files(self) -> List[Path]:
        """Discover all .md files in /web_food directory recursively."""
        markdown_files = []
        
        try:
            for file_path in self.web_food_dir.rglob("*.md"):
                if file_path.is_file():
                    markdown_files.append(file_path)
        except Exception as e:
            logger.error("Error discovering markdown files: %s", e)
        
        return sorted(markdown_files)
    
    def _extract_metadata(self, content: str, file_path: Path) -> tuple[str, Set[str]]:
        """Extract category and tags from document content."""
        category = ""
        tags = set()
        
        lines = content.split("\n")
        
        # Simple frontmatter parsing
        in_frontmatter = False
        for line in lines:
            stripped = line.strip()
            
            if stripped == "---":
                in_frontmatter = not in_frontmatter
                continue
            
            if in_frontmatter:
                if stripped.startswith("category:"):
                    category = stripped.split(":", 1)[1].strip().strip('"\'')
                elif stripped.startswith("tags:"):
                    tags_str = stripped.split(":", 1)[1].strip()
                    # Handle bracket notation
                    if tags_str.startswith("[") and tags_str.endswith("]"):
                        tags_str = tags_str[1:-1]
                    tags.update(tag.strip().strip('"\'') for tag in tags_str.split(","))
                elif stripped.startswith("tag:"):
                    tag = stripped.split(":", 1)[1].strip().strip('"\'')
                    tags.add(tag)
        
        # Infer category from file path if not in frontmatter
        if not category:
            parent_dir = file_path.parent.name
            if parent_dir != str(self.web_food_dir):
                category = parent_dir
        
        # Default category
        if not category:
            category = "general"
        
        return category, tags
    
    def _load_document(self, file_path: Path) -> Optional[WebFoodDocument]:
        """Load a single document from file."""
        try:
            relative_path = str(file_path.relative_to(self.web_food_dir))
            content = file_path.read_text(encoding="utf-8")
            
            file_hash = self._calculate_file_hash(file_path)
            modified_at = file_path.stat().st_mtime
            size = file_path.stat().st_size
            
            category, tags = self._extract_metadata(content, file_path)
            
            document = WebFoodDocument(
                path=relative_path,
                content=content,
                hash=file_hash,
                modified_at=modified_at,
                size=size,
                indexed_at=time.time(),
                category=category,
                tags=tags,
            )
            
            return document
            
        except Exception as e:
            logger.error("Error loading document %s: %s", file_path, e)
            return None
    
    def _load_all(self) -> None:
        """Load all documents from /web_food directory."""
        logger.info("[WEB_FOOD] Loading documents from %s", self.web_food_dir)
        
        markdown_files = self._discover_markdown_files()
        
        loaded_count = 0
        total_size = 0
        
        for file_path in markdown_files:
            document = self._load_document(file_path)
            if document:
                self._documents[document.path] = document
                self._fingerprints[document.path] = document.hash
                
                # Update category index
                if document.category not in self._category_index:
                    self._category_index[document.category] = []
                self._category_index[document.category].append(document)
                
                # Update tag index
                for tag in document.tags:
                    if tag not in self._tag_index:
                        self._tag_index[tag] = []
                    self._tag_index[tag].append(document)
                
                loaded_count += 1
                total_size += document.size
        
        # Update statistics
        self._stats["total_documents"] = loaded_count
        self._stats["total_size_bytes"] = total_size
        self._stats["last_load_time"] = time.time()
        
        logger.info("[WEB_FOOD] Loaded %d documents (%d bytes)", loaded_count, total_size)
    
    def detect_changes(self) -> List[WebFoodChange]:
        """Detect changes in /web_food directory since last check."""
        changes = []
        current_files = set()
        
        # Get current file state
        markdown_files = self._discover_markdown_files()
        for file_path in markdown_files:
            relative_path = str(file_path.relative_to(self.web_food_dir))
            current_files.add(relative_path)
            
            current_hash = self._calculate_file_hash(file_path)
            current_modified = file_path.stat().st_mtime
            
            if relative_path not in self._fingerprints:
                # New file
                changes.append(WebFoodChange(
                    change_type="added",
                    path=relative_path,
                    new_hash=current_hash,
                ))
            elif self._fingerprints[relative_path] != current_hash:
                # Modified file
                changes.append(WebFoodChange(
                    change_type="modified",
                    path=relative_path,
                    old_hash=self._fingerprints[relative_path],
                    new_hash=current_hash,
                ))
        
        # Check for deleted files
        for existing_path in self._fingerprints:
            if existing_path not in current_files:
                changes.append(WebFoodChange(
                    change_type="deleted",
                    path=existing_path,
                    old_hash=self._fingerprints[existing_path],
                ))
        
        # Update statistics
        self._stats["last_change_detection_time"] = time.time()
        self._stats["total_changes_detected"] += len(changes)
        
        if changes:
            logger.info("[WEB_FOOD] Detected %d changes", len(changes))
            for change in changes:
                logger.debug("[WEB_FOOD] %s: %s", change.change_type, change.path)
        
        return changes
    
    def reload_changes(self, changes: List[WebFoodChange]) -> None:
        """Reload documents based on detected changes."""
        for change in changes:
            if change.change_type == "added":
                self._handle_added(change)
            elif change.change_type == "modified":
                self._handle_modified(change)
            elif change.change_type == "deleted":
                self._handle_deleted(change)
        
        # Update change history
        self._change_history.extend(changes)
        
        # Trim history to last 100 changes
        if len(self._change_history) > 100:
            self._change_history = self._change_history[-100:]
    
    def _handle_added(self, change: WebFoodChange) -> None:
        """Handle a newly added file."""
        file_path = self.web_food_dir / change.path
        document = self._load_document(file_path)
        
        if document:
            self._documents[document.path] = document
            self._fingerprints[document.path] = document.hash
            
            # Update category index
            if document.category not in self._category_index:
                self._category_index[document.category] = []
            self._category_index[document.category].append(document)
            
            # Update tag index
            for tag in document.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                self._tag_index[tag].append(document)
            
            self._stats["total_documents"] += 1
            self._stats["total_size_bytes"] += document.size
            
            logger.info("[WEB_FOOD] Added: %s", change.path)
    
    def _handle_modified(self, change: WebFoodChange) -> None:
        """Handle a modified file."""
        file_path = self.web_food_dir / change.path
        
        # Remove old document from indexes
        if change.path in self._documents:
            old_doc = self._documents[change.path]
            
            # Remove from category index
            if old_doc.category in self._category_index:
                self._category_index[old_doc.category] = [
                    d for d in self._category_index[old_doc.category]
                    if d.path != change.path
                ]
            
            # Remove from tag index
            for tag in old_doc.tags:
                if tag in self._tag_index:
                    self._tag_index[tag] = [
                        d for d in self._tag_index[tag]
                        if d.path != change.path
                    ]
            
            # Update size stats
            self._stats["total_size_bytes"] -= old_doc.size
        
        # Load new document
        document = self._load_document(file_path)
        
        if document:
            self._documents[document.path] = document
            self._fingerprints[document.path] = document.hash
            
            # Update category index
            if document.category not in self._category_index:
                self._category_index[document.category] = []
            self._category_index[document.category].append(document)
            
            # Update tag index
            for tag in document.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                self._tag_index[tag].append(document)
            
            self._stats["total_size_bytes"] += document.size
            
            logger.info("[WEB_FOOD] Modified: %s", change.path)
    
    def _handle_deleted(self, change: WebFoodChange) -> None:
        """Handle a deleted file."""
        if change.path in self._documents:
            document = self._documents[change.path]
            
            # Remove from category index
            if document.category in self._category_index:
                self._category_index[document.category] = [
                    d for d in self._category_index[document.category]
                    if d.path != change.path
                ]
            
            # Remove from tag index
            for tag in document.tags:
                if tag in self._tag_index:
                    self._tag_index[tag] = [
                        d for d in self._tag_index[tag]
                        if d.path != change.path
                    ]
            
            # Update stats
            self._stats["total_documents"] -= 1
            self._stats["total_size_bytes"] -= document.size
            
            # Remove from registries
            del self._documents[change.path]
            del self._fingerprints[change.path]
            
            logger.info("[WEB_FOOD] Deleted: %s", change.path)
    
    def check_and_reload(self) -> bool:
        """Check for changes and reload if any detected."""
        changes = self.detect_changes()
        if changes:
            self.reload_changes(changes)
            return True
        return False
    
    def get_document(self, path: str) -> Optional[WebFoodDocument]:
        """Get a document by path."""
        return self._documents.get(path)
    
    def get_documents_by_category(self, category: str) -> List[WebFoodDocument]:
        """Get all documents in a category."""
        return self._category_index.get(category, []).copy()
    
    def get_documents_by_tag(self, tag: str) -> List[WebFoodDocument]:
        """Get all documents with a specific tag."""
        return self._tag_index.get(tag, []).copy()
    
    def search(self, query: str, limit: int = 5) -> List[WebFoodDocument]:
        """Search documents by content (simple keyword matching)."""
        query_lower = query.lower()
        scored_documents = []
        
        for document in self._documents.values():
            # Simple keyword matching
            content_lower = document.content.lower()
            score = 0
            
            # Exact phrase match
            if query_lower in content_lower:
                score += 10
            
            # Individual word matches
            query_words = query_lower.split()
            for word in query_words:
                if word in content_lower:
                    score += 2
            
            # Category match
            if query_lower in document.category.lower():
                score += 5
            
            # Tag match
            for tag in document.tags:
                if query_lower in tag.lower():
                    score += 3
            
            if score > 0:
                scored_documents.append((score, document))
        
        # Sort by score and return top results
        scored_documents.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_documents[:limit]]
    
    def get_relevant_content(self, query: str, max_tokens: int = 1000) -> str:
        """Get relevant content for a query, respecting token limits."""
        relevant_docs = self.search(query, limit=3)
        
        if not relevant_docs:
            return ""
        
        # Build context string
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Approximate 4 chars per token
        
        for doc in relevant_docs:
            if total_chars >= max_chars:
                break
            
            # Add document header
            header = f"\n--- From {doc.path} ({doc.category}) ---\n"
            if total_chars + len(header) > max_chars:
                break
            
            context_parts.append(header)
            total_chars += len(header)
            
            # Add content (truncated if needed)
            remaining_chars = max_chars - total_chars
            if remaining_chars > 0:
                content = doc.content[:remaining_chars]
                context_parts.append(content)
                total_chars += len(content)
        
        return "".join(context_parts)
    
    def get_all_content(self) -> str:
        """Get all /web_food content (use with caution)."""
        all_parts = []
        for doc in sorted(self._documents.values(), key=lambda d: d.path):
            all_parts.append(f"\n--- {doc.path} ({doc.category}) ---\n")
            all_parts.append(doc.content)
        
        return "".join(all_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get loader statistics."""
        return {
            **self._stats,
            "categories": list(self._category_index.keys()),
            "tags": list(self._tag_index.keys()),
            "recent_changes": [
                {
                    "type": c.change_type,
                    "path": c.path,
                    "detected_at": c.detected_at,
                }
                for c in self._change_history[-10:]
            ],
        }
    
    def get_document_list(self) -> List[Dict[str, Any]]:
        """Get list of all documents with metadata."""
        return [doc.to_dict() for doc in self._documents.values()]


# Global instance
web_food_loader = WebFoodLoader()
