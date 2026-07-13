"""Enhanced text normalization for JARVIS NLP pipeline.

Production-grade normalizer that handles:
- Unicode normalization and accent stripping
- Contraction expansion
- Filler/politeness word removal
- Hindi/Hinglish transliteration and SOV→SVO reordering
- Spelling correction via edit distance
- Emoji/slang expansion
- Number word expansion
- Repeated character collapsing
- Punctuation normalization
"""

from __future__ import annotations

import re
import unicodedata
from difflib import get_close_matches

# ════════════════════════════════════════════════════════════════════
# DATA DICTIONARIES
# ════════════════════════════════════════════════════════════════════

# ── Hindi/Hinglish → English transliteration map ──
_HINDI_MAP: dict[str, str] = {
    # Verbs
    "kholo": "open", "khol": "open", "kholna": "open",
    "band karo": "close", "band kar": "close", "band": "close",
    "chala": "play", "chalao": "play", "chalana": "play",
    "play karo": "play",
    "search karo": "search", "search kar": "search",
    "dhundh": "search", "dhundho": "search", "dhundna": "search",
    "batao": "tell", "bata": "tell", "batana": "tell",
    "dikhao": "show", "dikha": "show", "dikhana": "show",
    "maro": "do", "kar": "do", "karo": "do", "karna": "do",
    "hatao": "remove", "hatana": "remove",
    "delete karo": "delete", "delete kar": "delete",
    "on kar": "turn on", "on karo": "turn on",
    "off kar": "turn off", "off karo": "turn off",
    "bhul": "close", "bhul jao": "close",
    # Volume
    "volume badhao": "volume up", "volume badha": "volume up",
    "volume ghatao": "volume down", "volume ghata": "volume down",
    "awaz band": "mute", "awaz chalu": "unmute",
    "aawaz band": "mute", "aawaz chalu": "unmute",
    "sund": "mute", "suno": "unmute",
    # Brightness
    "light kam": "brightness down", "light zyada": "brightness up",
    "brightness kam": "brightness down", "brightness zyada": "brightness up",
    "roshni kam": "brightness down", "roshni zyada": "brightness up",
    # System
    "band kar": "close", "chalu kar": "turn on", "band kar": "turn off",
    "restart kar": "restart", "reboot kar": "restart",
    # Common phrases
    "mere": "my", "mera": "my", "meri": "my",
    "tumhara": "your", "tera": "your",
    "yeh": "this", "woh": "that",
    "kya": "what", "kab": "when", "kahan": "where", "kyun": "why",
    "kaun": "who", "kaise": "how",
    "download": "downloads", "folder": "folder",
    "photo": "photo", "photo dikha": "show photo",
    "music chala": "play music", "gaana chala": "play music",
    "browser open kar": "open browser",
    "wifi band kar": "turn off wifi", "wifi chalu kar": "turn on wifi",
    "bluetooth band kar": "turn off bluetooth", "bluetooth chalu kar": "turn on bluetooth",
}

# ── Verbs that Hindi map translates to (used for SOV→SVO reordering) ──
_HINDI_VERB_TARGETS: set[str] = {
    "open", "close", "play", "search", "tell", "show", "do",
    "remove", "delete", "turn on", "turn off",
    "volume up", "volume down", "mute", "unmute",
    "brightness down", "brightness up",
    "restart", "turn off wifi", "turn on wifi",
    "turn off bluetooth", "turn on bluetooth",
}

# ── Filler words to strip ──
_FILLERS: set[str] = {
    # Politeness
    "please", "pls", "plz", "kindly", "if you don't mind",
    # Attention grabbers
    "hey", "yo", "bro", "buddy", "mate", "dude", "man",
    "jarvis", "assistant",
    # Hesitations
    "uh", "um", "hmm", "ah", "oh", "erm", "ugh",
    # Hedging phrases
    "can you", "could you", "would you", "will you",
    "can u", "could u", "would u", "will u",
    "do you think you can", "is it possible to",
    "i want to", "i need to", "i'd like to",
    "i wanna", "i gotta", "i got to",
    "help me", "go ahead",
    "right now", "real quick", "just",
    "actually", "basically", "literally",
    "make sure to", "be sure to",
    "hey can you", "hey could you", "hey would you",
    "yo can you", "yo could you",
    "ok", "okay", "k", "kk",
    "yes", "no", "yeah", "yep", "nope", "nah",
    "thanks", "thank you", "thx", "ty", "tysm",
    "sorry", "excuse me",
    "btw", "by the way",
    "imo", "imho",
    "info", "information",
}

# ── Contraction expansion ──
_CONTRACTIONS: dict[str, str] = {
    "what's": "what is", "whatre": "what are", "whats": "what is",
    "what'll": "what will", "what'd": "what did",
    "how's": "how is", "hows": "how is",
    "how'll": "how will", "how'd": "how did",
    "where's": "where is", "wheres": "where is",
    "who's": "who is", "whos": "who is",
    "it's": "it is", "its": "it is",
    "that's": "that is", "thats": "that is",
    "this's": "this is",
    "there's": "there is", "theres": "there is",
    "they're": "they are", "theyre": "they are",
    "we're": "we are", "were": "we are",
    "you're": "you are", "youre": "you are",
    "he's": "he is", "shes": "she is", "she's": "she is",
    "i'm": "i am", "im": "i am",
    "i've": "i have", "ive": "i have",
    "i'll": "i will", "ill": "i will",
    "i'd": "i would",
    "don't": "do not", "dont": "do not",
    "doesn't": "does not", "doesnt": "does not",
    "didn't": "did not", "didnt": "did not",
    "won't": "will not", "wont": "will not",
    "wouldn't": "would not", "wouldnt": "would not",
    "can't": "cannot", "cant": "cannot",
    "couldn't": "could not", "couldnt": "could not",
    "shouldn't": "should not", "shouldnt": "should not",
    "isn't": "is not", "isnt": "is not",
    "aren't": "are not", "arent": "are not",
    "wasn't": "was not", "wasnt": "was not",
    "weren't": "were not", "werent": "were not",
    "hasn't": "has not", "hasnt": "has not",
    "haven't": "have not", "havent": "have not",
    "hadn't": "had not", "hadnt": "had not",
    "let's": "let us", "lets": "let us",
    "gonna": "going to", "wanna": "want to", "gotta": "got to",
    "kinda": "kind of", "sorta": "sort of",
    "lemme": "let me", "gimme": "give me",
    "ain't": "is not", "y'all": "you all",
    "nothin": "nothing", "everythin": "everything",
    "somethin": "something", "anythin": "anything",
}

# ── Unicode accent map ──
_ACCENT_MAP: dict[str, str] = {
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "á": "a", "à": "a", "â": "a", "ä": "a",
    "í": "i", "ì": "i", "î": "i", "ï": "i",
    "ó": "o", "ò": "o", "ô": "o", "ö": "o",
    "ú": "u", "ù": "u", "û": "u", "ü": "u",
    "ñ": "n", "ç": "c", "ß": "ss",
}

# ── Number words ──
_NUMBER_WORDS: dict[str, str] = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90", "hundred": "100", "thousand": "1000",
    "million": "1000000", "billion": "1000000000",
}

# ── Emoji → text expansion ──
_EMOJI_MAP: dict[str, str] = {
    "😀": "happy", "😃": "happy", "😄": "happy", "😁": "happy",
    "😆": "happy", "😂": "laughing", "🤣": "laughing",
    "😊": "smiling", "😇": "angel", "🙂": "smiling",
    "😉": "wink", "😌": "relaxed", "😍": "heart eyes",
    "🥰": "love", "😘": "kiss", "😗": "kissing",
    "😙": "kissing", "😚": "kissing", "😋": "yummy",
    "😛": "tongue", "😜": "tongue", "😝": "tongue",
    "🤑": "money", "🤗": "hug", "🤭": "oops",
    "🤔": "thinking", "🤐": "zip", "😐": "neutral",
    "😑": "annoyed", "😶": "silent", "😏": "smirk",
    "😒": "unamused", "🙄": "eye roll", "😬": "grimace",
    "🤥": "lying", "😌": "relieved", "😔": "pensive",
    "😪": "sleepy", "🤤": "drooling", "😴": "sleeping",
    "😷": "sick", "🤒": "sick", "🤕": "hurt",
    "🤢": "nauseous", "🤮": "vomit", "🥵": "hot",
    "🥶": "cold", "🥴": "dizzy", "😵": "dizzy",
    "🤯": "mind blown", "🤠": "cowboy", "🥳": "party",
    "😎": "cool", "🤓": "nerd", "🧐": "monocle",
    "😕": "confused", "😟": "worried", "🙁": "sad",
    "☹️": "sad", "😮": "surprised", "😯": "surprised",
    "😲": "astonished", "😳": "flushed", "🥺": "pleading",
    "😦": "frowning", "😧": "anguished", "😨": "fearful",
    "😰": "anxious", "😥": "sad", "😢": "crying",
    "😭": "crying", "😱": "screaming", "😖": "confounded",
    "😣": "persevere", "😞": "disappointed", "😓": "cold sweat",
    "😩": "weary", "😫": "tired", "🥱": "yawning",
    "😤": "angry", "😡": "angry", "🤬": "swearing",
    "👍": "good", "👎": "bad", "👏": "clap",
    "🙏": "please", "💪": "strong", "🎉": "celebrate",
    "❤️": "love", "💔": "broken heart", "⭐": "star",
    "🔥": "fire", "💯": "perfect", "✅": "done",
    "❌": "no", "⭕": "circle", "❓": "question",
    "❗": "exclamation", "💡": "idea", "🎵": "music",
    "🎶": "music", "📱": "phone", "💻": "computer",
    "🖥️": "computer", "⏰": "alarm", "📷": "camera",
    "📸": "camera", "🔒": "lock", "🔓": "unlock",
    "🔑": "key", "📁": "folder", "📂": "folder",
    "🗑️": "delete", "📝": "note", "✏️": "edit",
    "🔗": "link", "📧": "email", "💬": "chat",
    "🌍": "world", "🌎": "world", "🌏": "world",
    "🌙": "moon", "☀️": "sun", "🌈": "rainbow",
    "❄️": "snow", "⚡": "lightning", "🌧️": "rain",
}

# ── Internet slang / abbreviations ──
_SLANG_MAP: dict[str, str] = {
    "brb": "be right back", "ttyl": "talk to you later",
    "lol": "laughing out loud", "lmao": "laughing my ass off",
    "rofl": "rolling on floor laughing", "omg": "oh my god",
    "wtf": "what the fuck", "smh": "shaking my head",
    "tbh": "to be honest", "imo": "in my opinion",
    "imho": "in my humble opinion", "fyi": "for your information",
    "asap": "as soon as possible", "aka": "also known as",
    "btw": "by the way", "rn": "right now",
    "idk": "i don know", "irl": "in real life",
    "ngl": "not gonna lie", "fr": "for real",
    "istg": "i swear to god", "stfu": "shut the fuck up",
    "lmao": "laughing", "bruh": "bro",
    "fam": "family", "bros": "bros",
    "yeet": "throw", "slaps": "is good",
    "no cap": "no lie", "cap": "lie",
    "vibe": "feeling", "vibes": "feelings",
    "drip": "style", "flex": "show off",
    "sus": "suspicious", "bet": "okay",
    "deadass": "seriously", "finna": "going to",
    "aight": "alright", "aight": "alright",
    "wassup": "what is up", "sup": "what is up",
    "yolo": "you only live once",
    "gf": "girlfriend", "bf": "boyfriend",
    "dm": "direct message", "pm": "private message",
    "op": "original post", "tl;dr": "too long did not read",
    "ftw": "for the win", "lfg": "lets fucking go",
    "gg": "good game", "ez": "easy",
    "afk": "away from keyboard", "irl": "in real life",
    "smh": "shaking my head", "ngl": "not gonna lie",
    "fr fr": "for real for real", "istg": "i swear to god",
    "on god": "i swear", "dead": "very funny",
    "slay": "amazing", "periodt": "end of discussion",
    "say less": "understood", "bet": "okay",
    "say no more": "understood", "lowkey": "somewhat",
    "highkey": "very much", "lowkey": "slightly",
    "ong": "on god", "w": "win", "l": "loss",
    "goat": "greatest of all time",
    "mid": "mediocre", "cap": "lie",
}

# ── Known words for spelling correction ──
_KNOWN_WORDS: set[str] = {
    # Apps
    "notepad", "calculator", "chrome", "firefox", "edge", "explorer",
    "spotify", "discord", "steam", "obs", "vlc", "terminal",
    "powershell", "paint", "word", "excel", "powerpoint", "outlook",
    "teams", "slack", "zoom", "skype", "whatsapp", "telegram",
    "vscode", "pycharm", "intellij", "blender", "photoshop",
    "sublime", "brave", "opera", "safari",
    # Websites
    "youtube", "google", "github", "reddit", "twitter", "instagram",
    "facebook", "netflix", "amazon", "linkedin", "wikipedia",
    "stackoverflow", "gmail", "chatgpt", "twitch", "tiktok",
    "pinterest", "discord", "spotify",
    # Actions
    "open", "close", "search", "play", "stop", "pause",
    "volume", "brightness", "screenshot", "calculator",
    "weather", "news", "timer", "alarm", "remind",
    "remember", "save", "delete", "copy", "paste",
    "download", "upload", "send", "receive",
    "minimize", "maximize", "restore", "switch",
    "shutdown", "restart", "reboot", "sleep", "lock",
    # Folders
    "downloads", "documents", "desktop", "pictures", "music", "videos",
    "home", "recycle", "bin",
    # Common
    "time", "date", "day", "today", "tomorrow", "yesterday",
    "weather", "temperature", "forecast",
    "battery", "power", "charge", "wifi", "bluetooth",
    "internet", "network", "speed", "test",
    "cpu", "ram", "memory", "disk", "storage",
    "screen", "display", "monitor", "mouse", "keyboard",
    "file", "folder", "document", "image", "video",
    "music", "song", "artist", "album", "playlist",
    "photo", "picture", "camera", "webcam",
    "email", "message", "call", "phone",
    "code", "program", "script", "project",
    "git", "github", "repository", "commit", "push", "pull",
    "python", "javascript", "java", "html", "css",
    "api", "database", "server", "client",
    "news", "headlines", "article", "blog",
    "stock", "price", "market", "finance",
    "recipe", "cook", "food", "restaurant",
    "movie", "film", "show", "series", "episode",
    "book", "read", "library",
    "game", "play", "gaming",
    "music", "song", "listen", "play",
    "joke", "funny", "laugh", "humor",
    "quote", "inspire", "motivate",
    "fact", "trivia", "knowledge",
    "translate", "language", "word",
    "math", "calculate", "solve", "equation",
    "password", "encrypt", "decrypt",
    "backup", "restore", "sync",
    "settings", "preferences", "config",
    "help", "info", "about", "status",
    "list", "show", "get", "set", "add", "remove",
    "find", "search", "look", "check",
    "tell", "say", "speak", "read", "write",
    "send", "receive", "share", "post",
    "connect", "disconnect", "login", "logout",
    "start", "stop", "pause", "resume",
    "enable", "disable", "toggle", "switch",
    "increase", "decrease", "raise", "lower",
    "bright", "dim", "light", "dark",
    "loud", "quiet", "mute", "unmute",
    "fast", "slow", "quick", "speed",
    "big", "small", "large", "tiny",
    "new", "old", "fresh", "latest",
    "good", "bad", "best", "worst",
    "first", "last", "next", "previous",
    "left", "right", "up", "down",
    "top", "bottom", "front", "back",
    "all", "none", "some", "every",
    "now", "then", "today", "tomorrow",
    "always", "never", "sometimes", "often",
    "here", "there", "everywhere",
    "this", "that", "these", "those",
    "what", "where", "when", "who", "how", "why",
    "which", "whose", "whom",
}

# ════════════════════════════════════════════════════════════════════
# NORMALIZATION FUNCTIONS
# ════════════════════════════════════════════════════════════════════


def _strip_accents(text: str) -> str:
    """Remove accents and normalize unicode."""
    text = unicodedata.normalize("NFKD", text)
    result = []
    for char in text:
        if char in _ACCENT_MAP:
            result.append(_ACCENT_MAP[char])
        elif not unicodedata.combining(char):
            result.append(char)
    return "".join(result)


def _expand_contractions(text: str) -> str:
    """Expand contractions like 'what's' → 'what is'."""
    words = text.split()
    expanded = []
    for word in words:
        if word in _CONTRACTIONS:
            expanded.append(_CONTRACTIONS[word])
        else:
            expanded.append(word)
    return " ".join(expanded)


def _remove_fillers(text: str) -> str:
    """Remove filler words and phrases."""
    for filler in sorted(_FILLERS, key=len, reverse=True):
        pattern = rf"\b{re.escape(filler)}\b"
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def _apply_hindi_map(text: str) -> str:
    """Apply Hindi/Hinglish transliteration mappings."""
    for hindi, english in sorted(_HINDI_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        text = text.replace(hindi, english)
    return text


def _reorder_hinglish_sov(text: str) -> str:
    """Reorder Hinglish SOV (Subject-Object-Verb) to English SVO."""
    words = text.split()
    for verb in sorted(_HINDI_VERB_TARGETS, key=len, reverse=True):
        verb_words = verb.split()
        n = len(verb_words)
        if n <= len(words) and words[-n:] == verb_words and len(words) > n:
            rest = words[:-n]
            return verb + " " + " ".join(rest)
    return text


def _collapse_repeated_chars(text: str) -> str:
    """Collapse repeated characters: 'heyyyy' → 'hey', 'plzzzz' → 'plz'."""
    return re.sub(r"(.)\1{2,}", r"\1\1", text)


def _expand_emoji(text: str) -> str:
    """Expand emojis to text descriptions."""
    for emoji, desc in _EMOJI_MAP.items():
        text = text.replace(emoji, f" {desc} ")
    return text


def _expand_slang(text: str) -> str:
    """Expand internet slang abbreviations."""
    words = text.split()
    expanded = []
    for word in words:
        if word in _SLANG_MAP:
            expanded.append(_SLANG_MAP[word])
        else:
            expanded.append(word)
    return " ".join(expanded)


def _normalize_punctuation(text: str) -> str:
    """Normalize punctuation: remove excessive punctuation, normalize quotes."""
    # Remove repeated punctuation
    text = re.sub(r"([!?.]){2,}", r"\1", text)
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(""", "'").replace(""", "'")
    # Remove special characters but keep basic punctuation
    text = re.sub(r"[^\w\s.,!?;:'\-/+@#$%^&*()]", " ", text)
    return text


def _expand_number_words(text: str) -> str:
    """Expand number words to digits: 'set volume to fifty' → 'set volume to 50'."""
    words = text.split()
    expanded = []
    for word in words:
        if word in _NUMBER_WORDS:
            expanded.append(_NUMBER_WORDS[word])
        else:
            expanded.append(word)
    return " ".join(expanded)


def _correct_spelling(text: str) -> str:
    """Correct common misspellings using edit distance against known words."""
    words = text.split()
    corrected = []
    for word in words:
        # Skip short words, numbers, and words that look like URLs/paths
        if len(word) <= 2 or word.isdigit() or "/" in word or "." in word:
            corrected.append(word)
            continue
        # Skip if word is already known
        if word in _KNOWN_WORDS:
            corrected.append(word)
            continue
        # Try to find close matches with high threshold to avoid false corrections
        matches = get_close_matches(word, _KNOWN_WORDS, n=1, cutoff=0.88)
        if matches:
            corrected.append(matches[0])
        else:
            corrected.append(word)
    return " ".join(corrected)


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()


# ════════════════════════════════════════════════════════════════════
# MAIN NORMALIZATION PIPELINE
# ════════════════════════════════════════════════════════════════════


def normalize(text: str) -> str:
    """Full normalization pipeline.

    Steps:
        1. Unicode normalize and strip accents
        2. Lowercase
        3. Expand contractions
        4. Collapse repeated characters
        5. Expand emojis
        6. Expand internet slang
        7. Normalize punctuation
        8. Apply Hindi/Hinglish mappings
        9. Remove filler words
        10. Reorder Hinglish SOV → SVO
        11. Expand number words
        12. Correct spelling
        13. Normalize whitespace

    Args:
        text: Raw user input

    Returns:
        Normalized, lowercased, cleaned text
    """
    if not text:
        return ""

    text = _strip_accents(text)
    text = text.lower()
    text = _expand_contractions(text)
    text = _collapse_repeated_chars(text)
    text = _expand_emoji(text)
    text = _expand_slang(text)
    text = _normalize_punctuation(text)
    text_before_hindi = text
    text = _apply_hindi_map(text)
    text = _remove_fillers(text)
    if text != text_before_hindi:
        text = _reorder_hinglish_sov(text)
    text = _expand_number_words(text)
    text = _correct_spelling(text)
    text = _normalize_whitespace(text)

    return text


def normalize_keep_case(text: str) -> str:
    """Normalize but preserve original casing (for proper nouns, URLs)."""
    if not text:
        return ""
    text = _strip_accents(text)
    text = _expand_contractions(text.lower()).title()
    text = _apply_hindi_map(text.lower())
    text = _remove_fillers(text)
    text = _normalize_whitespace(text)
    return text


def normalize_for_matching(text: str) -> str:
    """Aggressive normalization for intent matching.

    This is more aggressive than normalize() - it strips everything
    that isn't a core content word, for maximum pattern matching flexibility.
    """
    text = normalize(text)
    # Remove articles
    text = re.sub(r"\b(a|an|the)\b", "", text)
    # Remove prepositions
    text = re.sub(r"\b(to|for|on|in|at|by|with|from|of|about)\b", "", text)
    # Remove auxiliary verbs
    text = re.sub(r"\b(is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|shall|should|may|might|can|could)\b", "", text)
    return _normalize_whitespace(text)
