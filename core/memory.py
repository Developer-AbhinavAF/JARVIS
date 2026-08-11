"""core/memory.py — Persistent Hybrid Memory System for JARVIS vNext++.

Three-layer view:
1. Working memory  — session cache (per-process, in-memory).
2. Short-term      — conversation context carried by the agent loop / history.
3. Long-term       — durable JSON store (memories.json) with IDs, timestamps,
                     supersession, deduplication and hybrid retrieval
                     (exact/lexical + token-semantic fuzzy).

Long-term storage survives process/session/model restarts. Legacy flat files
(facts.json, preferences.json, goals.json, relationships.json) are migrated
into the structured store on startup and kept in sync by set_fact /
set_preference so existing callers keep working unchanged.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

VALID_MEMORY_TYPES = {
    "fact",
    "preference",
    "identity",
    "relationship",
    "goal",
    "project",
    "decision",
    "event",
    "instruction",
    "task",
    "observation",
}

_LEGACY_TYPE_MAP = {
    "facts": "fact",
    "preferences": "preference",
    "goals": "goal",
    "relationships": "relationship",
    "mistakes": "observation",
}

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "am", "what", "which", "who", "whom", "whose", "my", "mine", "your",
    "yours", "our", "ours", "i", "me", "we", "us", "you", "it", "its",
    "this", "that", "these", "those", "to", "of", "for", "on", "in", "at",
    "by", "with", "from", "up", "down", "out", "off", "over", "under",
    "do", "does", "did", "have", "has", "had", "not", "no", "and", "or",
    "but", "if", "then", "so", "because", "as", "here", "there", "when",
    "where", "why", "how", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "too", "very",
    "can", "will", "just", "should", "would", "could", "may", "might",
    "must", "about", "than", "into", "please", "s", "re", "ve", "d", "ll",
    "don", "t", "dont", "remember", "recall", "saved", "save", "stored",
    "store", "memorize", "forget", "know", "want", "need", "used", "use",
    "using", "say", "said", "tell", "told", "ask", "asked", "go", "get",
}

_TYPE_HINTS = [
    (("brother", "sister", "mother", "father", "friend", "wife", "husband",
      "partner", "mom", "dad", "family"), "relationship"),
    (("prefer", "preference", "preferences", "favorite", "favourite",
      "like", "love"), "preference"),
    (("project", "repo", "repository", "codebase"), "project"),
    (("goal", "aim", "objective", "dream", "target"), "goal"),
    (("meeting", "appointment", "birthday", "anniversary", "deadline",
      "event", "schedule", "date"), "event"),
    (("task", "todo", "to-do", "reminder", "list"), "task"),
    (("instruction", "rule", "always ", "never ", "must ", "should "),
     "instruction"),
    (("decision", "decided", "chose", "choice"), "decision"),
    (("name", "creator", "identity", "age"), "identity"),
]


@dataclass
class EpisodicMemory:
    date: str
    location: str
    context: str
    outcome: str
    importance: float = 1.0
    lessons: List[str] = field(default_factory=list)


def _tokenize(text: str) -> List[str]:
    """Lowercase word tokens with light stemming and stopword removal."""
    if not text:
        return []
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    out: List[str] = []
    for tok in tokens:
        tok = tok.strip("'")
        if len(tok) < 2 or tok in _STOPWORDS:
            continue
        if tok.endswith("ing") and len(tok) > 5:
            tok = tok[:-3]
        elif tok.endswith("ed") and len(tok) > 4:
            tok = tok[:-2]
        elif tok.endswith("ly") and len(tok) > 4:
            tok = tok[:-2]
        elif tok.endswith("es") and len(tok) > 4:
            tok = tok[:-2]
        out.append(tok)
    return out


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: Any) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _normalize_type(memory_type: Any) -> str:
    t = str(memory_type or "fact").strip().lower()
    t = _LEGACY_TYPE_MAP.get(t, t)
    return t if t in VALID_MEMORY_TYPES else "fact"


def _infer_type(text: Optional[str]) -> str:
    low = (text or "").lower()
    for words, mem_type in _TYPE_HINTS:
        if any(w in low for w in words):
            return mem_type
    return "fact"


def extract_memory_intent(
    text: str,
) -> Optional[Dict[str, Any]]:
    """Deterministically detect an explicit memory-save request.

    Recognizes: remember/save/store/note/keep in mind/don't forget ...
    Returns a structured intent {content, key, value, memory_type, explicit}
    or None when the text is not an explicit save request.
    """
    if not text or not str(text).strip():
        return None

    original = " ".join(str(text).split())

    if not re.search(
        r"\b(?:please\s+)?(?:remember|save|store|note\s+down|note\b|"
        r"memorize|keep\s+in\s+mind|don'?t\s+forget|do\s+not\s+forget)\b",
        original,
        re.IGNORECASE,
    ):
        return None

    rest = re.sub(
        r"^(?:please\s+)?(?:remember|save|store|note\s+down|memorize|"
        r"keep\s+in\s+mind|don'?t\s+forget|do\s+not\s+forget|note)\b",
        "",
        original,
        count=1,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r"^\s*(?:that|this|it|the\s+following)\b\s*",
        "",
        rest,
        flags=re.IGNORECASE,
    ).strip(" :;,-")

    if not rest:
        return None

    key: Optional[str] = None
    value: Optional[str] = None
    content: Optional[str] = None

    kv = re.match(
        r"^my\s+([a-z][\w\s'’-]{1,60}?)\s+(?:is|are|was|were)\s+(.+)$",
        rest,
        re.IGNORECASE,
    )
    if kv:
        key = kv.group(1).strip()
        value = kv.group(2).strip()
        content = f"My {key} is {value}"
    else:
        av = re.match(
            r"^my\s+([\w\s'’-]{1,60}?)\s+as\s+(.+)$",
            rest,
            re.IGNORECASE,
        )
        if av:
            key = av.group(1).strip()
            value = av.group(2).strip()
            content = f"My {key} is {value}"

    if content is None:
        content = rest

    memory_type = _infer_type(key or content)

    return {
        "content": content,
        "key": key,
        "value": value,
        "memory_type": memory_type,
        "explicit": True,
    }


class UnifiedMemory:
    """Persistent hybrid memory with a backward-compatible public API."""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._session_cache: Dict[str, Any] = {}
        self._facts: Dict[str, Any] = {}
        self._preferences: Dict[str, Any] = {}
        self._goals: Dict[str, Any] = {}
        self._projects: Dict[str, Any] = {}
        self._relationships: Dict[str, Any] = {}
        self._episodic: List[Dict[str, Any]] = []
        self._memories: List[Dict[str, Any]] = []
        self._legacy_files: Dict[str, bool] = {}

        self._load_all()
        self._migrate_legacy()

    # ------------------------------------------------------------------
    # LOADING / PERSISTENCE
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        for filename in (
            "facts.json",
            "preferences.json",
            "goals.json",
            "projects.json",
            "relationships.json",
        ):
            self._legacy_files[filename] = (
                self.memory_dir / filename
            ).exists()

        self._facts = self._load_file(
            "facts.json",
            {"name": "Abhinav", "creator": "Abhinav"},
        )
        self._preferences = self._load_file(
            "preferences.json",
            {"style": "concise", "mode": "execution-first"},
        )
        self._goals = self._load_file(
            "goals.json",
            {"active_goal": "Build JARVIS AGI OS"},
        )
        self._projects = self._load_file("projects.json", {})
        self._relationships = self._load_file(
            "relationships.json",
            {"creator": "Abhinav"},
        )
        self._episodic = self._load_file_list("episodic.json")
        self._memories = self._load_file_list("memories.json")

    def _load_file(
        self,
        filename: str,
        default: Dict[str, Any],
    ) -> Dict[str, Any]:
        filepath = self.memory_dir / filename
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    out: Dict[str, Any] = {}
                    for item in data:
                        if isinstance(item, dict):
                            key = (
                                item.get("title")
                                or item.get("name")
                                or item.get("id")
                                or str(item)
                            )
                            out[str(key)] = item
                    return out if out else default
                if isinstance(data, dict):
                    return data
                return default
            except Exception:
                logger.error("MEMORY_LOAD_FAILURE file=%s", filename)
                return default
        return default

    def _load_file_list(self, filename: str) -> List[Dict[str, Any]]:
        filepath = self.memory_dir / filename
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    def _save_file(self, filename: str, data: Any) -> bool:
        try:
            with open(self.memory_dir / filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as exc:
            logger.error(
                "MEMORY_STORE_FAILURE file=%s error=%s",
                filename,
                exc,
            )
            return False

    def _persist_memories(self) -> bool:
        return self._save_file("memories.json", self._memories)

    def _verified_on_disk(self, memory_id: str) -> bool:
        try:
            path = self.memory_dir / "memories.json"
            if not path.exists():
                return False
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return isinstance(data, list) and any(
                isinstance(m, dict) and m.get("id") == memory_id
                for m in data
            )
        except Exception:
            return False

    def _migrate_legacy(self) -> None:
        """Import legacy flat stores into the structured memories index.

        Idempotent: legacy entries are mapped to deterministic IDs so a
        re-run never creates duplicates.
        """
        legacy: List[Dict[str, Any]] = []
        existing_ids = {m.get("id") for m in self._memories}

        # Only on-disk legacy data is migrated — in-memory defaults never
        # become persistent memories.
        for store, mem_type, filename in (
            (self._facts, "fact", "facts.json"),
            (self._preferences, "preference", "preferences.json"),
            (self._goals, "goal", "goals.json"),
            (self._relationships, "relationship", "relationships.json"),
        ):
            if not self._legacy_files.get(filename):
                continue
            for key, value in self._iter_kv(store):
                entry_id = self._content_id(mem_type, key, str(value))
                if entry_id in existing_ids:
                    continue
                legacy.append({
                    "id": entry_id,
                    "type": mem_type,
                    "key": str(key),
                    "content": f"{key}: {value}",
                    "value": value,
                    "created_at": _iso_now(),
                    "updated_at": _iso_now(),
                    "supersedes": None,
                    "superseded_by": None,
                    "active": True,
                    "explicit": False,
                    "confidence": 0.8,
                    "source": "legacy",
                })
                existing_ids.add(entry_id)

        if legacy:
            self._memories.extend(legacy)
            self._persist_memories()
            logger.info(
                "MEMORY_MIGRATE legacy=%d entries imported",
                len(legacy),
            )

    # ------------------------------------------------------------------
    # ID / NORMALIZATION HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _content_id(
        memory_type: str,
        key: str,
        content: str,
    ) -> str:
        payload = "|".join([
            memory_type,
            " ".join((key or "").lower().split()),
            " ".join((content or "").lower().split()),
        ])
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    # ------------------------------------------------------------------
    # WORKING MEMORY (session cache)
    # ------------------------------------------------------------------

    def set_session_cache(self, key: str, value: Any) -> None:
        self._session_cache[key] = value

    def get_session_cache(self, key: str) -> Optional[Any]:
        return self._session_cache.get(key)

    # ------------------------------------------------------------------
    # LEGACY BACK-COMPAT ACCESSORS (kept in sync with the index)
    # ------------------------------------------------------------------

    def get_fact(self, key: str) -> Optional[Any]:
        return self._facts.get(key.lower().strip())

    def set_fact(self, key: str, value: Any) -> None:
        key_norm = key.lower().strip()
        self._facts[key_norm] = value
        self._save_file("facts.json", self._facts)
        self.store(
            content=f"{key}: {value}",
            memory_type="fact",
            key=key,
            value=value,
            explicit=False,
            source="set_fact",
            confidence=0.9,
        )

    def get_preference(self, key: str) -> Optional[Any]:
        return self._preferences.get(key.lower().strip())

    def set_preference(self, key: str, value: Any) -> None:
        key_norm = key.lower().strip()
        self._preferences[key_norm] = value
        self._save_file("preferences.json", self._preferences)
        self.store(
            content=f"{key}: {value}",
            memory_type="preference",
            key=key,
            value=value,
            explicit=False,
            source="set_preference",
            confidence=0.9,
        )

    def add_episode(self, episode: EpisodicMemory) -> None:
        self._episodic.append(asdict(episode))
        self._save_file("episodic.json", self._episodic)

    @staticmethod
    def _iter_kv(store: Any) -> List[tuple]:
        if isinstance(store, dict):
            return list(store.items())
        if isinstance(store, list):
            pairs = []
            for item in store:
                if isinstance(item, dict):
                    key = (
                        item.get("title")
                        or item.get("name")
                        or item.get("id")
                        or str(item)
                    )
                    value = (
                        item.get("description")
                        or item.get("title")
                        or str(item)
                    )
                    pairs.append((str(key), str(value)))
            return pairs
        return []

    # ------------------------------------------------------------------
    # CANONICAL WRITE — the only durable memory write path
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        memory_type: str = "fact",
        key: Optional[str] = None,
        value: Any = None,
        explicit: bool = False,
        confidence: float = 1.0,
        source: str = "user",
    ) -> Dict[str, Any]:
        """Persist one memory entry and return a structured result.

        Contract: validate -> normalize -> deterministic ID -> timestamp ->
        deduplicate/supersede -> durable write -> on-disk verification.
        """
        start = time.perf_counter()

        content_norm = " ".join(str(content or "").split())
        if not content_norm:
            logger.info("MEMORY_STORE_START id=none type=%s (empty content)", memory_type)
            logger.info("MEMORY_STORE_FAILURE reason=empty_content")
            return {
                "success": False,
                "stored": False,
                "memory_id": None,
                "action": "rejected",
                "error": "empty_content",
            }

        mem_type = _normalize_type(memory_type)

        try:
            conf = float(confidence)
            conf = 0.0 if conf < 0.0 else (1.0 if conf > 1.0 else conf)
        except (TypeError, ValueError):
            conf = 1.0

        key_norm = " ".join(str(key or "").split()) or None
        value_norm = value
        now = _iso_now()

        entry_id = self._content_id(
            mem_type,
            key_norm or "",
            content_norm,
        )
        logger.info(
            "MEMORY_STORE_START id=%s type=%s key=%s source=%s",
            entry_id,
            mem_type,
            key_norm,
            source,
        )

        superseded_id: Optional[str] = None
        action = "created"
        existing = next(
            (m for m in self._memories if m.get("id") == entry_id),
            None,
        )

        if existing is not None:
            existing["content"] = content_norm
            if value_norm is not None:
                existing["value"] = value_norm
            existing["updated_at"] = now
            existing["active"] = True
            existing["explicit"] = bool(
                existing.get("explicit") or explicit
            )
            existing["confidence"] = max(
                float(existing.get("confidence", conf)),
                conf,
            )
            if source:
                existing["source"] = source
            action = "updated"
            logger.info(
                "MEMORY_DEDUP id=%s (idempotent update, no duplicate)",
                entry_id,
            )
        else:
            if key_norm:
                prior = [
                    m for m in self._memories
                    if m.get("active")
                    and m.get("type") == mem_type
                    and (m.get("key") or "").lower() == key_norm.lower()
                ]
                if prior:
                    prior.sort(
                        key=lambda m: _parse_iso(m.get("updated_at", "")),
                        reverse=True,
                    )
                    old = prior[0]
                    old["active"] = False
                    old["superseded_by"] = entry_id
                    superseded_id = old["id"]
                    action = "superseded"
                    logger.info(
                        "MEMORY_SUPERSEDE old=%s new=%s key=%s",
                        old["id"],
                        entry_id,
                        key_norm,
                    )

            self._memories.append({
                "id": entry_id,
                "type": mem_type,
                "key": key_norm,
                "content": content_norm,
                "value": value_norm,
                "created_at": now,
                "updated_at": now,
                "supersedes": superseded_id,
                "superseded_by": None,
                "active": True,
                "explicit": bool(explicit),
                "confidence": conf,
                "source": source,
            })

        persisted = self._persist_memories()
        verified = self._verified_on_disk(entry_id)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if persisted and verified:
            logger.info(
                "MEMORY_STORE_SUCCESS id=%s type=%s action=%s "
                "latency_ms=%.2f",
                entry_id,
                mem_type,
                action,
                latency_ms,
            )
            return {
                "success": True,
                "stored": True,
                "memory_id": entry_id,
                "action": action,
                "supersedes": superseded_id,
                "type": mem_type,
            }

        logger.error(
            "MEMORY_STORE_FAILURE id=%s action=%s persisted=%s "
            "verified=%s",
            entry_id,
            action,
            persisted,
            verified,
        )
        return {
            "success": False,
            "stored": False,
            "memory_id": entry_id,
            "action": action,
            "error": "persistence_verification_failed",
        }

    # ------------------------------------------------------------------
    # HYBRID RETRIEVAL — exact + lexical + token-semantic + recency
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Rank active memories against a natural-language query.

        Signals: exact key phrase, word overlap (key/content/value),
        fuzzy token similarity, explicitness, confidence, recency.
        Superseded memories are excluded. Returns entries with a `score`.
        """
        start = time.perf_counter()
        q_text = " ".join(str(query or "").split()).lower()

        if not q_text:
            logger.info("MEMORY_RETRIEVE_START query='' (empty)")
            logger.info("MEMORY_RETRIEVE_EMPTY query='' no_terms")
            return []

        logger.info(
            "MEMORY_RETRIEVE_START query='%s'",
            q_text[:120],
        )

        q_tokens = _tokenize(q_text)
        now_ts = time.time()
        scored: List[tuple] = []

        for m in self._memories:
            if not m.get("active"):
                continue

            key_tokens = _tokenize(m.get("key", ""))
            content_tokens = _tokenize(m.get("content", ""))
            value_tokens = _tokenize(str(m.get("value", "")))

            score = 0.0

            key_phrase = " ".join(key_tokens)
            if key_phrase and key_phrase in q_text:
                score += 4.0

            token_hits = (
                len(set(q_tokens) & set(key_tokens)) * 2.0
                + len(set(q_tokens) & set(content_tokens)) * 1.0
                + len(set(q_tokens) & set(value_tokens)) * 1.5
            )
            score += token_hits

            if token_hits == 0.0 and q_tokens:
                for qt in q_tokens:
                    for candidate in (
                        set(key_tokens) | set(content_tokens) | set(value_tokens)
                    ):
                        if qt == candidate:
                            continue
                        ratio = SequenceMatcher(None, qt, candidate).ratio()
                        if ratio >= 0.82:
                            score += 0.8
                            break

            # A memory only matches when it shares actual terms with the
            # query — bonus signals never create matches on their own.
            if score <= 0.0:
                continue

            if m.get("explicit"):
                score += 0.6

            try:
                conf = float(m.get("confidence", 1.0))
            except (TypeError, ValueError):
                conf = 1.0
            score += conf * 0.5

            updated_ts = _parse_iso(m.get("updated_at", ""))
            age_days = (
                (now_ts - updated_ts) / 86400.0
                if updated_ts
                else 365.0
            )
            score += 0.5 * (0.9 ** max(0.0, age_days))

            scored.append((score, m))

        scored.sort(
            key=lambda item: (
                item[0],
                _parse_iso(item[1].get("updated_at", "")),
            ),
            reverse=True,
        )

        results = [
            dict(m, score=round(score, 3))
            for score, m in scored[: max(1, min(int(top_k), 20))]
        ]

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if results:
            logger.info(
                "MEMORY_RETRIEVE_RESULTS query='%s' count=%d "
                "latency_ms=%.2f ids=%s",
                q_text[:120],
                len(results),
                latency_ms,
                [r["id"] for r in results],
            )
        else:
            logger.info(
                "MEMORY_RETRIEVE_EMPTY query='%s' latency_ms=%.2f",
                q_text[:120],
                latency_ms,
            )

        return results

    def search(self, query: str) -> Optional[str]:
        """Backward-compatible single-hit search (fast, key-first)."""
        query_clean = " ".join(str(query or "").lower().split())

        for k, v in self._iter_kv(self._facts):
            if k.lower() in query_clean:
                return f"Fact [{k}]: {v}"

        for k, v in self._iter_kv(self._preferences):
            if k.lower() in query_clean:
                return f"Preference [{k}]: {v}"

        for k, v in self._iter_kv(self._goals):
            if k.lower() in query_clean:
                return f"Goal [{k}]: {v}"

        found = self.retrieve(query_clean, top_k=1)
        if not found:
            return None

        best = found[0]
        label = best.get("type", "fact").capitalize()
        key = best.get("key")
        if key:
            return f"{label} [{key}]: {best.get('value') or best.get('content')}"
        return str(best.get("value") or best.get("content"))

    def get_memory_summary(self) -> str:
        """Backward-compatible compact summary of recent active memories."""
        facts = [
            f"{m.get('key') or m.get('content')}: {m.get('value') or ''}"
            for m in self._memories
            if m.get("active") and m.get("type") == "fact"
        ][:3]
        goals = [
            f"{m.get('key') or m.get('content')}"
            for m in self._memories
            if m.get("active") and m.get("type") == "goal"
        ][:2]
        facts_str = ", ".join(facts)
        goals_str = ", ".join(goals)
        return f"Facts: {facts_str} | Goals: {goals_str}"

    def format_memories(
        self,
        entries: List[Dict[str, Any]],
        max_entries: int = 5,
    ) -> str:
        """Format retrieved memories as clean [MEMORY] blocks for prompts."""
        blocks: List[str] = []
        for m in entries[: max(1, min(int(max_entries), 10))]:
            mem_type = m.get("type", "fact")
            key = m.get("key") or "-"
            value = m.get("value")
            if value is None:
                value = m.get("content")
            try:
                conf = float(m.get("confidence", 1.0))
                conf_label = (
                    "high"
                    if conf >= 0.8
                    else ("medium" if conf >= 0.5 else "low")
                )
            except (TypeError, ValueError):
                conf_label = "medium"
            blocks.append(
                "[MEMORY]\n"
                f"Type: {mem_type}\n"
                f"Key: {key}\n"
                f"Value: {value}\n"
                f"Confidence: {conf_label}\n"
                f"Updated: {m.get('updated_at', '')}\n"
                "[/MEMORY]"
            )
        return "\n\n".join(blocks)

    # ------------------------------------------------------------------
    # LEGACY COMPAT SHIMS (used by legacy brain.py / interfaces)
    # ------------------------------------------------------------------

    def remember(
        self,
        key: str,
        value: Any,
        category: str = "facts",
    ) -> Dict[str, Any]:
        """Legacy remember() -> canonical store()."""
        mem_type = _normalize_type(_LEGACY_TYPE_MAP.get(category, category))
        return self.store(
            content=f"{key}: {value}",
            memory_type=mem_type,
            key=key,
            value=value,
            explicit=False,
            source="legacy_remember",
        )

    def recall(self, query: str, category: str = None) -> Optional[str]:
        """Legacy recall() -> canonical search()."""
        return self.search(query)


def get_memory() -> UnifiedMemory:
    """Legacy factory compatibility (brain.py / older interfaces)."""
    return unified_memory


unified_memory = UnifiedMemory()


__all__ = [
    "UnifiedMemory",
    "EpisodicMemory",
    "extract_memory_intent",
    "get_memory",
    "unified_memory",
]