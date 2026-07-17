"""Goal detection engine for JARVIS NLP.

Infers the hidden user objective behind a command by analyzing text
semantics, intent context, and extracted entities.
"""

from __future__ import annotations

from typing import Any

from .utils import (
    GoalCategory,
    remove_stop_words,
    semantic_similarity,
    tokenize,
    weighted_token_score,
)


# ════════════════════════════════════════════════════════════════════
# GOAL SIGNATURES
# ════════════════════════════════════════════════════════════════════

GOAL_SIGNATURES: dict[GoalCategory, str] = {
    GoalCategory.ENTERTAINMENT: (
        "user wants to be entertained, watch something, have fun, "
        "pass time, avoid boredom, play games, jokes, movies, shows"
    ),
    GoalCategory.PRODUCTIVITY: (
        "user wants to get work done, be efficient, manage tasks, "
        "organize schedule, set reminders, take notes, be productive"
    ),
    GoalCategory.PROGRAMMING: (
        "user wants to code, develop, write programs, work on projects, "
        "debug, compile, run code, software development, scripting"
    ),
    GoalCategory.COMMUNICATION: (
        "user wants to communicate, message, call, email someone, "
        "send a reply, reach out, talk, chat, contact"
    ),
    GoalCategory.INFORMATION: (
        "user wants to learn, know, understand, find information, "
        "search, look up, research, facts, answers, explain"
    ),
    GoalCategory.SHOPPING: (
        "user wants to buy, purchase, compare prices, find products, "
        "order, shop, deals, discounts, reviews, best product"
    ),
    GoalCategory.SYSTEM: (
        "user wants to control the computer, adjust settings, "
        "manage system, change configuration, install, uninstall, "
        "volume, brightness, wifi, bluetooth, power"
    ),
    GoalCategory.MEDIA: (
        "user wants to listen to music, watch videos, consume media, "
        "play songs, stream, podcasts, albums, artists"
    ),
    GoalCategory.FINANCE: (
        "user wants financial information, stock prices, market data, "
        "investments, portfolio, crypto, banking, transactions"
    ),
    GoalCategory.EDUCATION: (
        "user wants to study, learn a topic, take a course, practice, "
        "tutorials, courses, exam prep, flashcards, assignments"
    ),
    GoalCategory.HEALTH: (
        "user wants health info, exercise, nutrition, wellness, "
        "fitness, diet, symptoms, medication, sleep, mental health"
    ),
    GoalCategory.SOCIAL: (
        "user wants to interact on social media, check feeds, "
        "post content, likes, followers, share, trending"
    ),
}

# Pre-tokenized goal signatures for fast scoring
_GOAL_TOKENS: dict[GoalCategory, list[str]] = {
    cat: remove_stop_words(tokenize(desc))
    for cat, desc in GOAL_SIGNATURES.items()
}


# ════════════════════════════════════════════════════════════════════
# INTENT → GOAL MAPPING
# ════════════════════════════════════════════════════════════════════

_INTENT_GOAL_MAP: dict[str, GoalCategory] = {
    # Productivity
    "set_reminder": GoalCategory.PRODUCTIVITY,
    "create_reminder": GoalCategory.PRODUCTIVITY,
    "set_alarm": GoalCategory.PRODUCTIVITY,
    "create_alarm": GoalCategory.PRODUCTIVITY,
    "manage_task": GoalCategory.PRODUCTIVITY,
    "create_task": GoalCategory.PRODUCTIVITY,
    "take_note": GoalCategory.PRODUCTIVITY,
    "create_note": GoalCategory.PRODUCTIVITY,
    "schedule_meeting": GoalCategory.PRODUCTIVITY,
    "open_calendar": GoalCategory.PRODUCTIVITY,
    # Programming
    "run_code": GoalCategory.PROGRAMMING,
    "open_editor": GoalCategory.PROGRAMMING,
    "open_vscode": GoalCategory.PROGRAMMING,
    "open_terminal": GoalCategory.PROGRAMMING,
    "git_command": GoalCategory.PROGRAMMING,
    "install_package": GoalCategory.PROGRAMMING,
    "debug_code": GoalCategory.PROGRAMMING,
    "compile_code": GoalCategory.PROGRAMMING,
    # Communication
    "send_message": GoalCategory.COMMUNICATION,
    "send_email": GoalCategory.COMMUNICATION,
    "make_call": GoalCategory.COMMUNICATION,
    "start_meeting": GoalCategory.COMMUNICATION,
    "reply_message": GoalCategory.COMMUNICATION,
    # Information
    "search_web": GoalCategory.INFORMATION,
    "web_search": GoalCategory.INFORMATION,
    "search": GoalCategory.INFORMATION,
    "lookup": GoalCategory.INFORMATION,
    "define": GoalCategory.INFORMATION,
    "explain": GoalCategory.INFORMATION,
    "how_to": GoalCategory.INFORMATION,
    "what_is": GoalCategory.INFORMATION,
    # Shopping
    "buy_product": GoalCategory.SHOPPING,
    "search_product": GoalCategory.SHOPPING,
    "compare_prices": GoalCategory.SHOPPING,
    "add_to_cart": GoalCategory.SHOPPING,
    "check_deals": GoalCategory.SHOPPING,
    # System
    "open_app": GoalCategory.SYSTEM,
    "close_app": GoalCategory.SYSTEM,
    "change_setting": GoalCategory.SYSTEM,
    "adjust_volume": GoalCategory.SYSTEM,
    "adjust_brightness": GoalCategory.SYSTEM,
    "toggle_wifi": GoalCategory.SYSTEM,
    "toggle_bluetooth": GoalCategory.SYSTEM,
    "lock_screen": GoalCategory.SYSTEM,
    "shutdown": GoalCategory.SYSTEM,
    "restart": GoalCategory.SYSTEM,
    "screenshot": GoalCategory.SYSTEM,
    # Media
    "play_music": GoalCategory.MEDIA,
    "play_song": GoalCategory.MEDIA,
    "play_artist": GoalCategory.MEDIA,
    "play_album": GoalCategory.MEDIA,
    "play_video": GoalCategory.MEDIA,
    "pause_media": GoalCategory.MEDIA,
    "next_track": GoalCategory.MEDIA,
    "previous_track": GoalCategory.MEDIA,
    "play_podcast": GoalCategory.MEDIA,
    # Entertainment
    "play_game": GoalCategory.ENTERTAINMENT,
    "tell_joke": GoalCategory.ENTERTAINMENT,
    "movie_suggestion": GoalCategory.ENTERTAINMENT,
    "show_meme": GoalCategory.ENTERTAINMENT,
    "entertain": GoalCategory.ENTERTAINMENT,
    # Finance
    "stock_price": GoalCategory.FINANCE,
    "portfolio": GoalCategory.FINANCE,
    "crypto_price": GoalCategory.FINANCE,
    "market_data": GoalCategory.FINANCE,
    "balance": GoalCategory.FINANCE,
    "transaction": GoalCategory.FINANCE,
    # Education
    "study_topic": GoalCategory.EDUCATION,
    "find_course": GoalCategory.EDUCATION,
    "flashcards": GoalCategory.EDUCATION,
    "practice": GoalCategory.EDUCATION,
    "tutorial": GoalCategory.EDUCATION,
    # Health
    "health_info": GoalCategory.HEALTH,
    "exercise_plan": GoalCategory.HEALTH,
    "nutrition_info": GoalCategory.HEALTH,
    "symptom_check": GoalCategory.HEALTH,
    "meditation": GoalCategory.HEALTH,
    # Social
    "check_social_feed": GoalCategory.SOCIAL,
    "post_content": GoalCategory.SOCIAL,
    "share_post": GoalCategory.SOCIAL,
    "check_notifications": GoalCategory.SOCIAL,
}


# ════════════════════════════════════════════════════════════════════
# ENTITY TYPE → GOAL MAPPING
# ════════════════════════════════════════════════════════════════════

_ENTITY_GOAL_MAP: dict[str, GoalCategory] = {
    "code": GoalCategory.PROGRAMMING,
    "script": GoalCategory.PROGRAMMING,
    "function": GoalCategory.PROGRAMMING,
    "repo": GoalCategory.PROGRAMMING,
    "repository": GoalCategory.PROGRAMMING,
    "package": GoalCategory.PROGRAMMING,
    "compiler": GoalCategory.PROGRAMMING,
    "debugger": GoalCategory.PROGRAMMING,
    "editor": GoalCategory.PROGRAMMING,
    "vscode": GoalCategory.PROGRAMMING,
    "pycharm": GoalCategory.PROGRAMMING,
    "terminal": GoalCategory.PROGRAMMING,
    "music": GoalCategory.MEDIA,
    "song": GoalCategory.MEDIA,
    "artist": GoalCategory.MEDIA,
    "album": GoalCategory.MEDIA,
    "playlist": GoalCategory.MEDIA,
    "podcast": GoalCategory.MEDIA,
    "video": GoalCategory.MEDIA,
    "movie": GoalCategory.ENTERTAINMENT,
    "show": GoalCategory.ENTERTAINMENT,
    "game": GoalCategory.ENTERTAINMENT,
    "joke": GoalCategory.ENTERTAINMENT,
    "email": GoalCategory.COMMUNICATION,
    "message": GoalCategory.COMMUNICATION,
    "call": GoalCategory.COMMUNICATION,
    "contact": GoalCategory.COMMUNICATION,
    "reminder": GoalCategory.PRODUCTIVITY,
    "alarm": GoalCategory.PRODUCTIVITY,
    "task": GoalCategory.PRODUCTIVITY,
    "note": GoalCategory.PRODUCTIVITY,
    "calendar": GoalCategory.PRODUCTIVITY,
    "schedule": GoalCategory.PRODUCTIVITY,
    "product": GoalCategory.SHOPPING,
    "price": GoalCategory.SHOPPING,
    "buy": GoalCategory.SHOPPING,
    "cart": GoalCategory.SHOPPING,
    "deal": GoalCategory.SHOPPING,
    "stock": GoalCategory.FINANCE,
    "portfolio": GoalCategory.FINANCE,
    "crypto": GoalCategory.FINANCE,
    "bitcoin": GoalCategory.FINANCE,
    "market": GoalCategory.FINANCE,
    "setting": GoalCategory.SYSTEM,
    "volume": GoalCategory.SYSTEM,
    "brightness": GoalCategory.SYSTEM,
    "wifi": GoalCategory.SYSTEM,
    "bluetooth": GoalCategory.SYSTEM,
    "app": GoalCategory.SYSTEM,
    "course": GoalCategory.EDUCATION,
    "tutorial": GoalCategory.EDUCATION,
    "study": GoalCategory.EDUCATION,
    "exercise": GoalCategory.HEALTH,
    "workout": GoalCategory.HEALTH,
    "diet": GoalCategory.HEALTH,
    "symptom": GoalCategory.HEALTH,
    "medication": GoalCategory.HEALTH,
}


# ════════════════════════════════════════════════════════════════════
# GOAL DETECTOR
# ════════════════════════════════════════════════════════════════════

class GoalDetector:
    """Infers hidden user objectives from command text, intent, and entities.

    Uses a three-signal scoring approach:
    1. Semantic similarity between the user text and goal signatures.
    2. Intent-to-goal mapping (strong signal when available).
    3. Entity-to-goal mapping (keyword boost from extracted entities).

    The final score is a weighted combination of these signals.
    """

    # Scoring weights
    _WEIGHT_SEMANTIC: float = 0.50
    _WEIGHT_INTENT: float = 0.30
    _WEIGHT_ENTITY: float = 0.20

    # Minimum confidence to avoid returning UNKNOWN
    _CONFIDENCE_THRESHOLD: float = 0.15

    def detect(
        self,
        text: str,
        intent: str,
        entities: dict[str, Any],
    ) -> tuple[GoalCategory, float]:
        """Detect the user's hidden goal.

        Args:
            text: The normalized user input text.
            intent: The classified intent string.
            entities: Extracted entity dict (entity_type -> value).

        Returns:
            A tuple of (GoalCategory, confidence 0.0-1.0).
        """
        text_tokens = remove_stop_words(tokenize(text))
        if not text_tokens:
            return GoalCategory.UNKNOWN, 0.0

        # Signal 1: Semantic similarity against each goal signature
        semantic_scores: dict[GoalCategory, float] = {}
        for category in GoalCategory:
            if category == GoalCategory.UNKNOWN:
                continue
            ref_text = GOAL_SIGNATURES[category]
            ref_tokens = _GOAL_TOKENS[category]
            sim = semantic_similarity(text, ref_text)
            # Boost with weighted token overlap
            token_boost = weighted_token_score(text_tokens, ref_tokens)
            semantic_scores[category] = 0.7 * sim + 0.3 * token_boost

        # Signal 2: Intent mapping
        intent_goal = self._infer_from_intent(intent)

        # Signal 3: Entity mapping
        entity_goal = self._infer_from_entities(entities)

        # Combine signals per category
        best_category = GoalCategory.UNKNOWN
        best_score = 0.0

        for category in GoalCategory:
            if category == GoalCategory.UNKNOWN:
                continue

            score = self._WEIGHT_SEMANTIC * semantic_scores.get(category, 0.0)

            if intent_goal == category:
                score += self._WEIGHT_INTENT * 1.0
            else:
                # Partial credit if intent is close — check intent tokens
                intent_tokens = remove_stop_words(tokenize(intent))
                goal_tokens = _GOAL_TOKENS[category]
                score += self._WEIGHT_INTENT * weighted_token_score(
                    intent_tokens, goal_tokens
                )

            if entity_goal == category:
                score += self._WEIGHT_ENTITY * 1.0
            else:
                # Partial credit from entity tokens
                entity_tokens = list(entities.values())
                entity_text_tokens = remove_stop_words(
                    tokenize(" ".join(str(v) for v in entity_tokens))
                )
                score += self._WEIGHT_ENTITY * weighted_token_score(
                    entity_text_tokens, goal_tokens
                )

            if score > best_score:
                best_score = score
                best_category = category

        # Clamp confidence
        confidence = min(best_score, 1.0)

        if confidence < self._CONFIDENCE_THRESHOLD:
            return GoalCategory.UNKNOWN, confidence

        return best_category, confidence

    def _infer_from_intent(self, intent: str) -> GoalCategory | None:
        """Map a classified intent to a goal category.

        Args:
            intent: The intent string (e.g. 'play_music', 'search_web').

        Returns:
            The matching GoalCategory, or None if no mapping exists.
        """
        if not intent:
            return None

        # Direct lookup
        direct = _INTENT_GOAL_MAP.get(intent.lower())
        if direct is not None:
            return direct

        # Prefix matching: try intent segments separated by underscore
        # e.g. "open_vscode_editor" → try "open_vscode_editor", "open_vscode", "open"
        parts = intent.lower().split("_")
        for length in range(len(parts), 0, -1):
            candidate = "_".join(parts[:length])
            match = _INTENT_GOAL_MAP.get(candidate)
            if match is not None:
                return match

        # Fallback: check if any intent tokens appear in goal signatures
        intent_tokens = remove_stop_words(tokenize(intent))
        best_cat = None
        best_overlap = 0.0
        for cat, ref_tokens in _GOAL_TOKENS.items():
            overlap = weighted_token_score(intent_tokens, ref_tokens)
            if overlap > best_overlap and overlap > 0.3:
                best_overlap = overlap
                best_cat = cat
        return best_cat

    def _infer_from_entities(self, entities: dict[str, Any]) -> GoalCategory | None:
        """Map extracted entities to a goal category.

        Args:
            entities: Dict of entity_type -> value from the NER stage.

        Returns:
            The matching GoalCategory, or None if no mapping exists.
        """
        if not entities:
            return None

        goal_votes: dict[GoalCategory, int] = {}
        for entity_type, value in entities.items():
            # Check entity type itself
            cat = _ENTITY_GOAL_MAP.get(entity_type.lower())
            if cat is not None:
                goal_votes[cat] = goal_votes.get(cat, 0) + 1

            # Check entity value as keyword
            val_str = str(value).lower()
            val_tokens = remove_stop_words(tokenize(val_str))
            for token in val_tokens:
                cat = _ENTITY_GOAL_MAP.get(token)
                if cat is not None:
                    goal_votes[cat] = goal_votes.get(cat, 0) + 1

        if not goal_votes:
            return None

        # Return the category with the most votes
        return max(goal_votes, key=goal_votes.get)  # type: ignore[arg-type]
