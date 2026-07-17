"""Semantic entity extraction engine for JARVIS NLP.

Extracts apps, websites, queries, paths, URLs, numbers, emails,
and platform references from user input using token-based semantic
matching rather than brittle regex patterns or substring checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from jarvis.nlp.utils import (
    Entity,
    remove_stop_words,
    tokenize,
    word_overlap_score,
)


# ════════════════════════════════════════════════════════════════════
# EXTRACTION RESULT
# ════════════════════════════════════════════════════════════════════

@dataclass
class ExtractionResult:
    """Container returned by :meth:`EntityExtractor.extract`.

    Wraps a dict of :class:`Entity` objects and exposes a convenience
    ``get`` / ``has`` API so that downstream modules (parameter parser,
    tool router, etc.) can access entity values without knowing about
    the internal ``Entity`` dataclass.
    """

    raw_text: str = ""
    cleaned_text: str = ""
    entities: dict[str, Entity] = field(default_factory=dict)
    confidence: float = 0.0

    # ── convenience accessors ───────────────────────────────────────

    def has(self, key: str) -> bool:
        """Return ``True`` if an entity with *key* was extracted."""
        return key in self.entities

    def get(self, key: str, default: Any = None) -> Any:
        """Return the *value* of an entity, or *default*.

        If the stored entity is an :class:`Entity` instance the ``.value``
        attribute is returned; otherwise the raw value is returned.
        """
        ent = self.entities.get(key)
        if ent is None:
            return default
        if isinstance(ent, Entity):
            return ent.value
        if isinstance(ent, dict):
            return ent.get("value", default)
        return ent

    def get_entity(self, key: str) -> Entity | None:
        """Return the full :class:`Entity` object for *key*."""
        ent = self.entities.get(key)
        if isinstance(ent, Entity):
            return ent
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialise entities to a plain dict of ``{key: value}``."""
        result: dict[str, Any] = {}
        for key, ent in self.entities.items():
            if isinstance(ent, Entity):
                result[key] = ent.value
            elif isinstance(ent, dict):
                result[key] = ent.get("value", ent)
            else:
                result[key] = ent
        return result

    def __len__(self) -> int:
        return len(self.entities)

    def __bool__(self) -> bool:
        return bool(self.entities)


# ════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASES
# ════════════════════════════════════════════════════════════════════

WEBSITES: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "medium": "https://medium.com",
    "devto": "https://dev.to",
    "gitlab": "https://gitlab.com",
    "bitbucket": "https://bitbucket.org",
    "npm": "https://www.npmjs.com",
    "pypi": "https://pypi.org",
    "docker hub": "https://hub.docker.com",
    "dockerhub": "https://hub.docker.com",
    "figma": "https://www.figma.com",
    "notion": "https://www.notion.so",
    "trello": "https://trello.com",
    "slack": "https://slack.com",
    "discord": "https://discord.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "pinterest": "https://www.pinterest.com",
    "tiktok": "https://www.tiktok.com",
    "quora": "https://www.quora.com",
    "coursera": "https://www.coursera.org",
    "udemy": "https://www.udemy.com",
    "leetcode": "https://leetcode.com",
    "geeksforgeeks": "https://www.geeksforgeeks.org",
    "chatgpt": "https://chat.openai.com",
    "openai": "https://openai.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
    "bing": "https://www.bing.com",
    "duckduckgo": "https://duckduckgo.com",
    "yahoo": "https://www.yahoo.com",
    "outlook": "https://outlook.live.com",
    "gmail": "https://mail.google.com",
    "drive": "https://drive.google.com",
    "onedrive": "https://onedrive.live.com",
    "dropbox": "https://www.dropbox.com",
    "canva": "https://www.canva.com",
    "steam": "https://store.steampowered.com",
    "epic games": "https://www.epicgames.com",
    "npmjs": "https://www.npmjs.com",
}

APPS: dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "mozilla firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    "brave browser": "brave",
    "opera": "opera",
    "vivaldi": "vivaldi",
    "safari": "safari",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "visual studio": "devenv",
    "sublime": "sublime_text",
    "sublime text": "sublime_text",
    "notepad": "notepad",
    "notepad++": "notepad++",
    "notepad plus plus": "notepad++",
    "atom": "atom",
    "intellij": "idea64",
    "intellij idea": "idea64",
    "pycharm": "pycharm64",
    "webstorm": "webstorm64",
    "android studio": "studio64",
    "terminal": "cmd",
    "powershell": "pwsh",
    "cmd": "cmd",
    "command prompt": "cmd",
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "task manager": "taskmgr",
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "teams": "ms-teams",
    "microsoft teams": "ms-teams",
    "zoom": "zoom",
    "skype": "skype",
    "obs": "obs64",
    "obs studio": "obs64",
    "photoshop": "photoshop",
    "illustrator": "illustrator",
    "premiere": "premiere",
    "premiere pro": "premiere",
    "after effects": "afterfx",
    "blender": "blender",
    "gimp": "gimp",
    "vlc": "vlc",
    "vlc media player": "vlc",
    "foobar": "foobar2000",
    "winamp": "winamp",
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpnt",
    "microsoft powerpoint": "powerpnt",
    "outlook": "outlook",
    "microsoft outlook": "outlook",
    "onenote": "onenote",
    "microsoft onenote": "onenote",
    "paint": "mspaint",
    "mspaint": "mspaint",
    "snipping tool": "snippingtool",
    "calculator": "calculator",
    "calc": "calculator",
    "notion": "notion",
    "trello": "trello",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "thunderbird": "thunderbird",
    "docker": "docker",
    "docker desktop": "docker desktop",
    "postman": "postman",
    "insomnia": "insomnia",
    "figma": "figma",
    "github desktop": "github",
    "tortoise": "tortoisegit",
    "tortoisegit": "tortoisegit",
    "winrar": "winrar",
    "7zip": "7zfm",
    "7-zip": "7zfm",
    "steam": "steam",
    "epic": "epicgameslauncher",
    "epic games": "epicgameslauncher",
}

FOLDERS: dict[str, str] = {
    "downloads": "~/Downloads",
    "download": "~/Downloads",
    "documents": "~/Documents",
    "document": "~/Documents",
    "desktop": "~/Desktop",
    "pictures": "~/Pictures",
    "picture": "~/Pictures",
    "images": "~/Pictures",
    "music": "~/Music",
    "videos": "~/Videos",
    "video": "~/Videos",
    "movies": "~/Videos",
    "temp": "~/AppData/Local/Temp",
    "temporary": "~/AppData/Local/Temp",
    "appdata": "~/AppData",
    "home": "~",
    "user": "~",
    "projects": "~/Projects",
    "project": "~/Projects",
    "code": "~/Projects",
    "repos": "~/Projects",
    "repository": "~/Projects",
    "workspace": "~/Projects",
    "work": "~/Projects",
    "github": "~/Projects",
    "src": "~/Projects",
    "source": "~/Projects",
}

PLATFORMS: dict[str, str] = {
    "reddit": "https://www.reddit.com/search/?q={query}",
    "github": "https://github.com/search?q={query}&type=repositories",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search={query}",
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "google": "https://www.google.com/search?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "stackoverflow": "https://stackoverflow.com/search?q={query}",
    "stack overflow": "https://stackoverflow.com/search?q={query}",
    "medium": "https://medium.com/search?q={query}",
    "twitter": "https://twitter.com/search?q={query}",
    "x": "https://x.com/search?q={query}",
    "linkedin": "https://www.linkedin.com/search/results/all/?keywords={query}",
    "amazon": "https://www.amazon.com/s?k={query}",
    "npm": "https://www.npmjs.com/search?q={query}",
    "pypi": "https://pypi.org/search/?q={query}",
    "dockerhub": "https://hub.docker.com/search?q={query}",
    "figma": "https://www.figma.com/community/search?resource_type=mixed&sort_by=relevancy&query={query}",
    "leetcode": "https://leetcode.com/problemset/?search={query}",
    "geeksforgeeks": "https://www.geeksforgeeks.org/search/?q={query}",
    "coursera": "https://www.coursera.org/search?query={query}",
    "udemy": "https://www.udemy.com/courses/search/?q={query}",
    "notion": "https://www.notion.so/search?q={query}",
    "quora": "https://www.quora.com/search?q={query}",
    "pinterest": "https://www.pinterest.com/search/pins/?q={query}",
    "tiktok": "https://www.tiktok.com/search?q={query}",
    "trello": "https://trello.com/search?q={query}",
    "openai": "https://chat.openai.com/?q={query}",
    "chatgpt": "https://chat.openai.com/?q={query}",
    "claude": "https://claude.ai/search?q={query}",
}


# ════════════════════════════════════════════════════════════════════
# SEMANTIC ENTITY EXTRACTOR
# ════════════════════════════════════════════════════════════════════

class SemanticEntityExtractor:
    """Extracts typed entities from user text via semantic token matching.

    Instead of checking ``token in entity_name`` (substring), this uses
    token-overlap and fuzzy-sequence ratios so that e.g. "githb" still
    matches "github", and "vs code" matches the key "vs code".
    """

    # Minimum score for an entity match to be accepted.
    MATCH_THRESHOLD: float = 0.45

    # ── public API ──────────────────────────────────────────────────

    def extract(
        self,
        text: str,
        intent: str,
        context: Any = None,
    ) -> ExtractionResult:
        """Extract all recognised entities from *text*.

        Parameters
        ----------
        text:
            Normalised user input.
        intent:
            The classified intent (e.g. ``"open_app"``, ``"search_web"``).
        context:
            Optional regex match object or context dict for
            resolving ambiguous references.

        Returns
        -------
        ExtractionResult
            Wrapper around extracted entities with ``get`` / ``has`` API.
        """
        entities: dict[str, Entity] = {}
        tokens = tokenize(text)
        content_tokens = remove_stop_words(tokens)
        # Normalize intent to lowercase for internal matching
        intent_lower = intent.lower() if intent else ""

        # ── URLs (highest priority – unambiguous) ───────────────
        url = self._extract_url(text)
        if url:
            entities["url"] = Entity(
                name="url",
                value=url,
                raw_value=url,
                confidence=1.0,
                entity_type="url",
            )

        # ── File / folder paths ─────────────────────────────────
        path = self._extract_path(text)
        if path:
            entities["path"] = Entity(
                name="path",
                value=path,
                raw_value=path,
                confidence=1.0,
                entity_type="path",
            )

        # ── Emails (scan raw text – tokenizer strips @) ─────────
        for match in re.finditer(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text):
            entities["email"] = Entity(
                name="email",
                value=match.group(0),
                raw_value=match.group(0),
                confidence=1.0,
                entity_type="email",
            )
            break

        # ── Numbers ─────────────────────────────────────────────
        for token in tokens:
            if token.isdigit():
                entities.setdefault(
                    "number",
                    Entity(
                        name="number",
                        value=token,
                        raw_value=token,
                        confidence=1.0,
                        entity_type="number",
                    ),
                )

        # ── Apps ────────────────────────────────────────────────
        if intent_lower in (
            "open_app", "close_app", "launch_app", "switch_app",
            "install_app", "uninstall_app", "update_app",
        ):
            name, score = self._find_best_entity_match(
                content_tokens, APPS,
            )
            if score >= self.MATCH_THRESHOLD:
                entities["app"] = Entity(
                    name="app",
                    value=APPS[name],
                    raw_value=name,
                    confidence=round(score, 3),
                    entity_type="app",
                    metadata={"canonical_name": name},
                )

        # ── Websites ────────────────────────────────────────────
        if intent_lower in (
            "open_website", "visit_site", "search_web", "browse",
        ):
            name, score = self._find_best_entity_match(
                content_tokens, WEBSITES,
            )
            if score >= self.MATCH_THRESHOLD:
                entities["website"] = Entity(
                    name="website",
                    value=WEBSITES[name],
                    raw_value=name,
                    confidence=round(score, 3),
                    entity_type="website",
                    metadata={"canonical_name": name},
                )

        # ── Platforms (for platform-specific searches) ──────────
        if intent_lower in (
            "search_web", "search_on_platform", "find_on",
            "browse", "lookup",
        ):
            name, score = self._find_best_entity_match(
                content_tokens, PLATFORMS,
            )
            if score >= self.MATCH_THRESHOLD:
                entities["platform"] = Entity(
                    name="platform",
                    value=name,
                    raw_value=name,
                    confidence=round(score, 3),
                    entity_type="platform",
                    metadata={
                        "canonical_name": name,
                        "search_url_template": PLATFORMS[name],
                    },
                )

        # ── Folders ─────────────────────────────────────────────
        if intent_lower in (
            "open_folder", "open_path", "open_file", "navigate",
            "save_to", "download_to",
        ):
            name, score = self._find_best_entity_match(
                content_tokens, FOLDERS,
            )
            if score >= self.MATCH_THRESHOLD:
                entities["folder"] = Entity(
                    name="folder",
                    value=FOLDERS[name],
                    raw_value=name,
                    confidence=round(score, 3),
                    entity_type="folder",
                    metadata={"canonical_name": name},
                )

        # ── Query / search term ─────────────────────────────────
        query = self._extract_query(text, intent, entities)
        if query:
            entities["query"] = Entity(
                name="query",
                value=query,
                raw_value=query,
                confidence=0.9,
                entity_type="query",
            )

        # ── Also set "target" for backward compat with param parser ─
        target_val = (
            entities.get("query")
            or entities.get("app")
            or entities.get("website")
            or entities.get("path")
            or entities.get("platform")
        )
        if target_val:
            raw = target_val.raw_value if isinstance(target_val, Entity) else str(target_val)
            val = target_val.value if isinstance(target_val, Entity) else str(target_val)
            entities["target"] = Entity(
                name="target",
                value=val,
                raw_value=raw,
                confidence=0.85,
                entity_type="target",
            )

        overall_confidence = max(
            (e.confidence for e in entities.values()), default=0.0,
        )

        return ExtractionResult(
            raw_text=text,
            cleaned_text=text,
            entities=entities,
            confidence=overall_confidence,
        )

    # ── matching helpers ────────────────────────────────────────────

    def _find_best_entity_match(
        self,
        tokens: list[str],
        knowledge_dict: dict[str, str],
    ) -> tuple[str, float]:
        """Return the best-matching entity name and its confidence score.

        Matching strategy (combined score):
        1. **Key-coverage** – fraction of the *entity key's* tokens that
           appear in the input (high when the input contains the key).
        2. **Fuzzy token match** – best ``SequenceMatcher`` ratio between
           each key-token and the closest input token (handles typos).
        3. **Sequence similarity** – ``SequenceMatcher`` ratio between
           the concatenated input and the entity key.
        4. **Substring bonus** – small reward for substring containment.
        """
        if not tokens:
            return "", 0.0

        input_set = set(tokens)
        input_str = " ".join(tokens)
        best_name = ""
        best_score = 0.0

        for key in knowledge_dict:
            key_tokens = tokenize(key)
            if not key_tokens:
                continue

            # Exact token coverage
            key_hits = sum(1 for kt in key_tokens if kt in input_set)
            key_coverage = key_hits / len(key_tokens)

            # Fuzzy token coverage – best SequenceMatcher per key token
            fuzzy_hits = 0.0
            for kt in key_tokens:
                best_token_ratio = max(
                    (SequenceMatcher(None, kt, it).ratio() for it in tokens),
                    default=0.0,
                )
                fuzzy_hits += best_token_ratio
            fuzzy_coverage = fuzzy_hits / len(key_tokens)

            # Sequence-level fuzzy ratio on full strings
            seq_score = SequenceMatcher(
                None, input_str, key,
            ).ratio()

            # Substring bonus (0.12 max)
            substring_bonus = 0.0
            if key in input_str:
                substring_bonus = 0.12
            elif input_str in key:
                substring_bonus = 0.10

            # When fuzzy match is strong but exact tokens miss (typo),
            # give extra weight to the fuzzy + sequence signals.
            if key_coverage == 0.0 and fuzzy_coverage > 0.75:
                combined = (
                    0.10 * key_coverage
                    + 0.40 * fuzzy_coverage
                    + 0.35 * seq_score
                    + substring_bonus
                )
            else:
                combined = (
                    0.35 * key_coverage
                    + 0.25 * fuzzy_coverage
                    + 0.25 * seq_score
                    + substring_bonus
                )

            if combined > best_score:
                best_score = combined
                best_name = key

        return best_name, best_score

    def _extract_query(
        self,
        text: str,
        intent: str,
        entities: dict[str, Entity],
    ) -> str | None:
        """Extract the search/topic portion of the input.

        Strategy: take all content tokens from *text*, then remove tokens
        that belong to already-identified entities (app, website, platform,
        folder) and intent-cue tokens so that only the user's actual
        search query remains.
        """
        content_tokens = remove_stop_words(tokenize(text))
        if not content_tokens:
            return None

        # Tokens to strip because they are structural / intent-cue words
        intent_cue_tokens = {
            "open", "launch", "run", "close", "kill",
            "search", "find", "lookup", "look", "browse", "go",
            "navigate", "visit", "play", "show", "display",
            "for", "about", "on", "in", "me", "please",
            "could", "would", "can", "want", "need",
        }

        # Collect tokens already claimed by an entity
        claimed: set[str] = set()
        for entity in entities.values():
            if isinstance(entity, Entity):
                # Don't claim tokens from number entities (numbers are often part of queries)
                if entity.entity_type == "number":
                    continue
                claimed.update(tokenize(entity.raw_value))
                if entity.entity_type == "app":
                    claimed.update(tokenize(entity.value))
                if entity.entity_type == "website":
                    claimed.update(tokenize(entity.value.split("//")[-1]))
                if entity.entity_type == "folder":
                    claimed.update(tokenize(entity.value))

        query_tokens = [
            t for t in content_tokens
            if t not in claimed and t not in intent_cue_tokens
        ]

        if not query_tokens:
            return None

        query = " ".join(query_tokens)
        return query if len(query) >= 2 else None

    def _extract_path(self, text: str) -> str | None:
        """Detect a file-system path in the raw text.

        Looks for drive-letter patterns (``D:\\``), UNC paths (``\\\\``),
        or home-relative paths (``~/``).
        """
        # Drive letter: D:\...
        for match in re.finditer(
            r"[A-Za-z]:\\[\w\s\\.\\\-/]+", text,
        ):
            return match.group(0).strip()

        # UNC path: \\server\share
        for match in re.finditer(
            r"\\\\[\w.]+\\[\w\s\\.\\\-/]+", text,
        ):
            return match.group(0).strip()

        # Home-relative: ~/...
        for match in re.finditer(
            r"~/[\w\s\\.\\\-/]+", text,
        ):
            return match.group(0).strip()

        return None

    def _extract_url(self, text: str) -> str | None:
        """Detect an HTTP/HTTPS URL in the raw text."""
        for match in re.finditer(
            r"https?://[^\s<>\"')]+", text,
        ):
            return match.group(0).strip()
        return None


# Alias used by jarvis.nlp.__init__
EntityExtractor = SemanticEntityExtractor
