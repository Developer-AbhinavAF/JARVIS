"""jarvis.learning_memory

Self-learning memory system for JARVIS.
Stores user corrections and learns from mistakes.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

from jarvis import config

logger = logging.getLogger(__name__)


class LearningMemory:
    """Self-learning system that remembers and corrects mistakes."""
    
    def __init__(self, db_path: str = None) -> None:
        """Initialize learning memory system."""
        import os
        if db_path:
            self.db_path = db_path
        else:
            # Use absolute path in JARVIS root directory from config
            self.db_path = os.path.join(config.JARVIS_ROOT, "jarvis_learning.db")
        
        logger.info(f"🧠 Learning memory DB path: {self.db_path}")
        
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self) -> None:
        """Create tables for learning memory."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Mistakes/corrections table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS corrections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_hash TEXT UNIQUE,
                        original_query TEXT,
                        wrong_response TEXT,
                        correct_response TEXT,
                        correction_type TEXT,
                        context TEXT,
                        timestamp TEXT,
                        occurrence_count INTEGER DEFAULT 1,
                        last_used TEXT
                    )
                """)
                
                # Pattern rules - extracted from corrections
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pattern_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern TEXT,
                        rule_type TEXT,
                        correction TEXT,
                        example_queries TEXT,
                        success_count INTEGER DEFAULT 1,
                        created TEXT
                    )
                """)
                
                # User preferences learned over time
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS learned_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT,
                        key TEXT,
                        value TEXT,
                        confidence REAL DEFAULT 0.5,
                        evidence_count INTEGER DEFAULT 1,
                        first_seen TEXT,
                        last_updated TEXT
                    )
                """)
                
                conn.commit()
                logger.info("✅ Learning memory database initialized")
        except Exception as e:
            logger.error(f"Failed to init learning memory: {e}")
    
    def _get_query_hash(self, query: str) -> str:
        """Generate hash for query for quick lookup."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def find_correction(self, query: str, threshold: float = 0.85) -> Optional[Dict]:
        """Find if there's a correction for similar query.
        
        Args:
            query: User's query
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            Correction dict if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # First try exact hash match
                query_hash = self._get_query_hash(query)
                cursor.execute(
                    "SELECT * FROM corrections WHERE query_hash = ?",
                    (query_hash,)
                )
                exact_match = cursor.fetchone()
                
                if exact_match:
                    # Update usage count
                    cursor.execute(
                        "UPDATE corrections SET occurrence_count = occurrence_count + 1, last_used = ? WHERE id = ?",
                        (datetime.now().isoformat(), exact_match['id'])
                    )
                    conn.commit()
                    return dict(exact_match)
                
                # Try similar queries
                cursor.execute("SELECT * FROM corrections")
                all_corrections = cursor.fetchall()
                
                best_match = None
                best_score = 0
                
                for corr in all_corrections:
                    similarity = self._similarity(query, corr['original_query'])
                    if similarity > threshold and similarity > best_score:
                        best_match = corr
                        best_score = similarity
                
                if best_match:
                    # Update usage
                    cursor.execute(
                        "UPDATE corrections SET occurrence_count = occurrence_count + 1, last_used = ? WHERE id = ?",
                        (datetime.now().isoformat(), best_match['id'])
                    )
                    conn.commit()
                    
                    match_dict = dict(best_match)
                    match_dict['similarity'] = best_score
                    return match_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Error finding correction: {e}")
            return None
    
    def save_correction(self, 
                       original_query: str, 
                       wrong_response: str, 
                       correct_response: str,
                       correction_type: str = "general",
                       context: str = None) -> bool:
        """Save a new correction when user points out a mistake.
        
        Args:
            original_query: What user asked
            wrong_response: What JARVIS incorrectly responded
            correct_response: The correct response
            correction_type: Type of correction (math, fact, format, etc.)
            context: Additional context
            
        Returns:
            True if saved successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query_hash = self._get_query_hash(original_query)
                
                # Check if correction already exists
                cursor.execute(
                    "SELECT id, occurrence_count FROM corrections WHERE query_hash = ?",
                    (query_hash,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing
                    cursor.execute(
                        """UPDATE corrections 
                           SET correct_response = ?, 
                               wrong_response = ?,
                               occurrence_count = occurrence_count + 1,
                               last_used = ?
                           WHERE id = ?""",
                        (correct_response, wrong_response, datetime.now().isoformat(), existing[0])
                    )
                else:
                    # Insert new
                    cursor.execute(
                        """INSERT INTO corrections 
                           (query_hash, original_query, wrong_response, correct_response, 
                            correction_type, context, timestamp, occurrence_count, last_used)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                        (query_hash, original_query, wrong_response, correct_response,
                         correction_type, context, datetime.now().isoformat(), datetime.now().isoformat())
                    )
                
                conn.commit()
                logger.info(f"💡 Correction saved for: {original_query[:50]}...")
                
                # Extract and save pattern rule
                self._extract_pattern_rule(original_query, correct_response, correction_type)
                
                return True
                
        except Exception as e:
            logger.error(f"Error saving correction: {e}")
            return False
    
    def _extract_pattern_rule(self, query: str, correct_response: str, correction_type: str) -> None:
        """Extract pattern from correction to apply to similar queries."""
        try:
            # Simple pattern extraction - can be enhanced with ML
            # For math problems, extract formula pattern
            if correction_type == "math":
                # Look for formula in correct response
                import re
                formula_patterns = [
                    r'(\w+)\s*=\s*([^\n]+)',  # X = Y pattern
                    r'([\d\s+\-*/()]+=[\d\s+\-*/()]+)'  # Equation pattern
                ]
                
                for pattern in formula_patterns:
                    match = re.search(pattern, correct_response)
                    if match:
                        rule = match.group(0)
                        self._save_pattern_rule(pattern, "math_formula", rule, query)
                        break
            
            # For facts, extract key information
            elif correction_type == "fact":
                # Save key fact
                self._save_pattern_rule(query.split()[0], "fact_check", correct_response, query)
                
        except Exception as e:
            logger.debug(f"Pattern extraction failed: {e}")
    
    def _save_pattern_rule(self, pattern: str, rule_type: str, correction: str, example: str) -> None:
        """Save extracted pattern rule."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """INSERT OR REPLACE INTO pattern_rules 
                       (pattern, rule_type, correction, example_queries, created)
                       VALUES (?, ?, ?, ?, ?)""",
                    (pattern, rule_type, correction, example, datetime.now().isoformat())
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Pattern save failed: {e}")
    
    def learn_preference(self, category: str, key: str, value: str, confidence: float = 0.5) -> bool:
        """Learn a user preference over time.
        
        Args:
            category: Preference category (e.g., 'music', 'format', 'style')
            key: Preference key
            value: Preference value
            confidence: Confidence level (0.0 to 1.0)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                # Check existing
                cursor.execute(
                    "SELECT confidence, evidence_count FROM learned_preferences WHERE category = ? AND key = ?",
                    (category, key)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update with weighted average
                    old_conf, count = existing
                    new_conf = (old_conf * count + confidence) / (count + 1)
                    
                    cursor.execute(
                        """UPDATE learned_preferences 
                           SET value = ?, confidence = ?, evidence_count = evidence_count + 1, last_updated = ?
                           WHERE category = ? AND key = ?""",
                        (value, new_conf, now, category, key)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO learned_preferences 
                           (category, key, value, confidence, evidence_count, first_seen, last_updated)
                           VALUES (?, ?, ?, ?, 1, ?, ?)""",
                        (category, key, value, confidence, now, now)
                    )
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error learning preference: {e}")
            return False
    
    def get_preference(self, category: str, key: str, min_confidence: float = 0.3) -> Optional[str]:
        """Get learned preference if confidence is high enough."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """SELECT value, confidence FROM learned_preferences 
                       WHERE category = ? AND key = ? AND confidence >= ?""",
                    (category, key, min_confidence)
                )
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                return None
                
        except Exception as e:
            logger.error(f"Error getting preference: {e}")
            return None
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about learning."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM corrections")
                total_corrections = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM pattern_rules")
                total_patterns = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM learned_preferences")
                total_preferences = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(occurrence_count) FROM corrections")
                total_applications = cursor.fetchone()[0] or 0
                
                return {
                    "total_corrections": total_corrections,
                    "total_patterns": total_patterns,
                    "total_preferences": total_preferences,
                    "total_applications": total_applications,
                    "learning_active": True
                }
                
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def get_all_corrections(self, limit: int = 50) -> List[Dict]:
        """Get all saved corrections."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM corrections ORDER BY occurrence_count DESC, timestamp DESC LIMIT ?",
                    (limit,)
                )
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting corrections: {e}")
            return []
    
    def verify_db(self) -> Dict[str, Any]:
        """Verify database exists and is valid."""
        import os
        
        result = {
            "db_path": self.db_path,
            "exists": False,
            "size": 0,
            "writable": False,
            "readable": False,
            "tables": []
        }
        
        try:
            # Check file exists
            result["exists"] = os.path.exists(self.db_path)
            if result["exists"]:
                result["size"] = os.path.getsize(self.db_path)
                result["writable"] = os.access(self.db_path, os.W_OK)
                result["readable"] = os.access(self.db_path, os.R_OK)
                
                # Check tables
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    result["tables"] = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"🔍 DB Verification: {result['exists']} | Size: {result['size']} bytes | Path: {self.db_path}")
            return result
            
        except Exception as e:
            logger.error(f"DB verification error: {e}")
            result["error"] = str(e)
            return result


# Global instance
learning_memory = LearningMemory()

# Registry for tool integration
LEARNING_REGISTRY = {
    "save_correction": learning_memory.save_correction,
    "find_correction": learning_memory.find_correction,
    "learn_preference": learning_memory.learn_preference,
    "get_learning_stats": learning_memory.get_learning_stats,
}
