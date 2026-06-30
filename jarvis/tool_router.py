"""Tool-first intent classifier and router for JARVIS.

Priority: Intent → Entity Extraction → Tool Execution → Result → LLM (fallback)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from jarvis import config
from jarvis.action_router import Action, ActionType

logger = logging.getLogger(__name__)


@dataclass
class ToolAction:
    name: str
    confidence: float
    handler: str
    params: dict[str, Any] = field(default_factory=dict)
    structured_action: Action | None = None


class ToolRouter:
    """Routes user input to the right tool based on intent matching."""

    def __init__(self) -> None:
        self._tools: list[dict[str, Any]] = []

    def register(
        self,
        name: str,
        patterns: list[str],
        handler: str,
        confidence: float = 0.85,
        extract: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self._tools.append({
            "name": name,
            "patterns": patterns,
            "handler": handler,
            "confidence": confidence,
            "extract": extract,
        })

    def route(self, text: str) -> ToolAction | None:
        cleaned = text.lower().strip()
        best: ToolAction | None = None

        for tool in self._tools:
            for pattern in tool["patterns"]:
                m = re.search(pattern, cleaned)
                if m:
                    params = {}
                    if tool["extract"]:
                        params = tool["extract"](cleaned)
                    structured_action = _build_structured_action(tool["handler"], cleaned, params)
                    action = ToolAction(
                        name=tool["name"],
                        confidence=tool["confidence"],
                        handler=tool["handler"],
                        params=params,
                        structured_action=structured_action,
                    )
                    if not best or action.confidence > best.confidence:
                        best = action
                    break

        return best


def _extract_query(text: str) -> dict[str, Any]:
    return {"query": _strip_command_prefix(text)}


def _extract_url_or_query(text: str) -> dict[str, Any]:
    url_m = re.search(r"https?://[^\s]+", text)
    if url_m:
        return {"url": url_m.group(0)}
    site_m = re.search(r"(?:open|launch|go\s+to|visit|navigate\s+to)\s+(.+)$", text)
    if site_m:
        return {"site": site_m.group(1).strip()}
    return {}


def _extract_city(text: str) -> dict[str, Any]:
    m = re.search(r"weather\s+(?:in|at|for)\s+(.+)", text)
    if m:
        return {"city": m.group(1).strip()}
    return {"city": ""}


def _extract_number(text: str) -> dict[str, Any]:
    m = re.search(r"(\d+)", text)
    return {"seconds": int(m.group(1)) if m else 30}


def _extract_expression(text: str) -> dict[str, Any]:
    for prefix in ["calculate ", "calc ", "what is ", "what's ", "solve "]:
        if text.startswith(prefix):
            return {"expression": text[len(prefix):].strip()}
    m = re.search(r"(\d+\s*[\+\-\*\/\%]\s*\d+)", text)
    if m:
        return {"expression": m.group(1)}
    return {"expression": text}


def _extract_symbol(text: str) -> dict[str, Any]:
    m = re.search(r"(?:stock|price|quote)\s+(?:(?:price|of|for)\s+)?(\w+)", text)
    if m:
        return {"symbol": m.group(1).upper()}
    words = text.split()
    for w in reversed(words):
        if w.isalpha() and len(w) <= 5:
            return {"symbol": w.upper()}
    return {"symbol": "AAPL"}


def _strip_command_prefix(text: str) -> str:
    cleaned = text.strip()
    for pattern in [
        r"^(?:search\s+(?:the\s+)?(?:web|internet)\s+for)\s+",
        r"^(?:google|look\s+up|search|find|play)\s+",
        r"\s+on\s+youtube$",
    ]:
        cleaned = re.sub(pattern, "", cleaned, count=1)
    return cleaned.strip()


_KNOWN_WEBSITES: dict[str, str] = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "reddit": "https://reddit.com",
    "twitter": "https://x.com",
    "x.com": "https://x.com",
    "instagram": "https://instagram.com",
    "facebook": "https://facebook.com",
    "netflix": "https://netflix.com",
    "spotify": "https://open.spotify.com",
    "amazon": "https://amazon.com",
    "linkedin": "https://linkedin.com",
    "whatsapp": "https://web.whatsapp.com",
}


def _build_structured_action(handler: str, text: str, params: dict[str, Any]) -> Action | None:
    if handler == "open_app":
        if params.get("url"):
            return Action(ActionType.OPEN_WEBSITE, params["url"])
        site = re.sub(r"\s+", " ", (params.get("site") or "").strip().lower())
        url = _KNOWN_WEBSITES.get(site)
        return Action(ActionType.OPEN_WEBSITE, url) if url else None

    if handler == "web_search":
        query = (params.get("query") or "").strip()
        return Action(ActionType.SEARCH_WEB, query) if query else None

    if handler == "search_youtube":
        query = (params.get("query") or "").strip()
        return Action(ActionType.YOUTUBE_SEARCH, query, {"query": query}) if query else None

    if handler == "play_youtube":
        query = (params.get("query") or "").strip()
        return Action(ActionType.YOUTUBE_PLAY, query, {"query": query}) if query else None

    if handler == "get_weather":
        city = (params.get("city") or "").strip()
        return Action(ActionType.GET_WEATHER, city, {"city": city}) if city else None

    if handler == "finnhub_market_news":
        topic = ""
        topic_m = re.search(r"(?:news|headlines)(?:\s+(?:about|on|in|of|for)\s+(.+))", text)
        if topic_m:
            topic = topic_m.group(1).strip()
        return Action(ActionType.GET_NEWS, topic, {"topic": topic})

    return None


# Global router with all built-in tool mappings
router = ToolRouter()

# ── YouTube ──
router.register("youtube_search", [
    r"search\s+.+\s+on\s+youtube",
    r"find\s+.+\s+on\s+youtube",
    r"youtube\s+search\s+",
], "search_youtube", 0.95, _extract_query)

router.register("youtube_play", [
    r"play\s+.+\s+on\s+youtube",
    r"play\s+.+\s+video",
    r"play\s+youtube\s+",
    r"watch\s+.+\s+on\s+youtube",
    r"play\s+",
], "play_youtube", 0.90, _extract_query)

# ── Open Website ──
router.register("open_website", [
    r"(?:open|launch|go\s+to|visit|navigate\s+to)\s+(youtube|google|gmail|github|stack\s*overflow|reddit|twitter|x\.com|instagram|facebook|netflix|spotify|amazon|linkedin|whatsapp)",
    r"(?:open|launch|go\s+to|visit)\s+(https?://[^\s]+)",
], "open_app", 0.95, _extract_url_or_query)

# ── Web Search ──
router.register("web_search", [
    r"search\s+(?:the\s+)?(?:web|internet)\s+for\s+",
    r"google\s+",
    r"look\s+up\s+",
    r"what\s+is\s+",
    r"who\s+is\s+",
    r"how\s+(?:to|do|does|can|would|should)",
    r"why\s+(?:is|are|do|does|did|can|would)",
    r"find\s+(?:information|details|about)\s+",
    r"latest\s+(?:news|updates?|trends?)\s+(?:about|on|in|of)\s+",
], "web_search", 0.80, _extract_query)

# ── Wikipedia ──
router.register("wikipedia", [
    r"wikipedia\s+",
    r"search\s+wikipedia\s+",
    r"look\s+up\s+on\s+wikipedia",
], "web_search", 0.80, _extract_query)

# ── Weather ──
router.register("weather", [
    r"weather\s+(?:in|at|for|of)\s+",
    r"(?:what'?s|what\s+is)\s+the\s+weather",
    r"(?:temperature|forecast)\s+(?:in|at|for)\s+",
], "get_weather", 0.95, _extract_city)

# ── News ──
router.register("news", [
    r"(?:latest|breaking|today'?s?|current)\s+(?:news|headlines)",
    r"(?:news|headlines)(?:\s+about|\s+on|\s+in|\s+of|\s+for)?",
    r"what'?s?\s+happening",
    r"market\s+news",
    r"latest\s+.+\s+news",
    r"news\s+update",
], "finnhub_market_news", 0.85)

# ── NASA ──
router.register("nasa_apod", [
    r"nasa\s+(?:apod|picture\s+of\s+the\s+day|astronomy\s+picture)",
    r"(?:picture|photo|image)\s+of\s+the\s+day\s+nasa",
], "nasa_apod", 0.95)

router.register("nasa_mars", [
    r"nasa\s+mars\s+(?:rover|photo|picture)",
    r"mars\s+rover\s+",
], "nasa_mars_rover", 0.90)

router.register("nasa_iss", [
    r"(?:iss|international\s+space\s+station)\s+(?:location|where|position|track)",
    r"where\s+is\s+the\s+iss",
], "nasa_iss", 0.90)

router.register("nasa_neo", [
    r"(?:near.?earth|neo|asteroid|comet)\s+(?:object|data|track|info)",
    r"asteroid\s+",
], "nasa_space_data", 0.85)

# ── Stocks ──
router.register("stock_quote", [
    r"(?:stock|share|price|quote)\s+(?:price|of|for|info|information)?\s*(?:\w+)",
    r"(?:\w+)\s+(?:stock|share)\s+(?:price|quote)",
], "finnhub_quote", 0.90, _extract_symbol)

# ── System ──
router.register("system_status", [
    r"(?:system|computer|pc)\s+(?:status|stats|info|information|health)",
    r"(?:show|get|check)\s+(?:system|computer)\s+(?:status|stats)",
    r"what'?s?\s+the\s+(?:system|computer)\s+(?:status|health)",
    r"how'?s?\s+(?:the\s+)?(?:system|computer|pc)\s+(?:doing|running)",
    r"performance\s+(?:status|stats|report)",
    r"system\s+monitoring",
], "get_system_stats", 0.95)

router.register("volume_control", [
    r"volume\s+(up|down|increase|decrease|raise|lower)",
    r"(?:turn\s+(?:it|the\s+volume)?\s+)?(up|down)\s+the\s+volume",
    r"mute\s+(?:audio|sound|volume)?",
    r"unmute\s+(?:audio|sound|volume)?",
    r"set\s+volume\s+(?:to\s+)?(\d+)",
], "volume_control", 0.95, lambda t: {"action": "up" if "up" in t or "increase" in t else "down" if "down" in t or "decrease" in t else "mute" if "mute" in t else "unmute" if "unmute" in t else "set", "value": int(m.group(1)) if (m := re.search(r"(\d+)", t)) else None})

router.register("open_app_cmd", [
    r"(?:open|launch|start|run)\s+(?:the\s+)?(app|application|program|software)\s+",
    r"(?:open|launch|start|run)\s+(notepad|calculator|chrome|firefox|edge|explorer|terminal|cmd|powershell|vscode|spotify|vlc|paint|word|excel|powerpoint)",
], "open_app", 0.90, lambda t: {"target": t})

router.register("close_app_cmd", [
    r"(?:close|kill|stop|exit|quit)\s+(?:the\s+)?(?:app|application|program|process)\s+",
    r"(?:close|kill|stop|exit)\s+(notepad|calculator|chrome|firefox|edge|explorer|terminal|cmd|vscode|spotify|vlc|paint)",
], "close_app", 0.90, lambda t: {"target": t})

router.register("list_apps", [
    r"(?:list|show|what)\s+(?:running\s+)?(?:apps?|applications?|programs?|processes?)",
    r"what'?s?\s+running",
    r"running\s+(?:apps?|applications?|programs?|processes?)",
], "list_running_apps", 0.90)

router.register("power_control", [
    r"(?:shut\s*down|shutdown|power\s*off|poweroff)\s+(?:the\s+)?(?:computer|pc|system)?",
    r"(?:restart|reboot)\s+(?:the\s+)?(?:computer|pc|system)?",
    r"(?:sleep|hibernate)\s+(?:the\s+)?(?:computer|pc|system)?",
    r"(?:lock|log\s*out)\s+(?:the\s+)?(?:computer|pc|system|session)?",
    r"(?:cancel|abort)\s+(?:shutdown|restart)",
], "system_power", 0.95, lambda t: {"action": "shutdown" if "shut" in t or "power off" in t else "restart" if "restart" in t or "reboot" in t else "sleep" if "sleep" in t or "hibernate" in t else "lock" if "lock" in t else "logout" if "log out" in t else "cancel_shutdown" if "cancel" in t else "shutdown"})

router.register("screenshot", [
    r"(?:take|get|capture)\s+(?:a\s+)?(?:screenshot|screen\s*shot|screen\s*capture|snapshot)",
    r"screenshot\s+(?:now|please)?",
], "screenshot", 0.95)

router.register("clipboard_get", [
    r"(?:get|show|read|what'?s?\s+on)\s+(?:the\s+)?(?:clipboard|clip\s*board)",
    r"what'?s?\s+(?:copied|copied\s+to\s+clipboard)",
], "clipboard_manager", 0.90, lambda t: {"action": "get"})

router.register("clipboard_copy", [
    r"copy\s+(?:this|that|the\s+following|to\s+clipboard)",
    r"copy\s+['\"]?(.+?)['\"]?\s+to\s+clipboard",
], "clipboard_manager", 0.85, lambda t: {"action": "copy", "text": t})

router.register("brightness_control", [
    r"brightness\s+(up|down|increase|decrease|raise|lower)",
    r"set\s+brightness\s+(?:to\s+)?(\d+)",
    r"(?:make\s+)?(?:it|screen|display)\s+(?:brighter|dimmer)",
], "brightness_control", 0.90, lambda t: {"action": "up" if "up" in t or "increase" in t or "brighter" in t else "down" if "down" in t or "decrease" in t or "dimmer" in t else "set", "value": int(m.group(1)) if (m := re.search(r"(\d+)", t)) else None})

# ── Entertainment ──
router.register("joke", [
    r"(?:tell|make|crack|give)\s+(?:me\s+)?(?:a\s+)?(?:joke|funny)",
    r"joke\s+(?:please|now)?",
], "get_joke", 0.95)

router.register("quote", [
    r"(?:give|tell|show|inspire)\s+(?:me\s+)?(?:a\s+)?(?:quote|inspiration|motivational)",
    r"quote\s+(?:of\s+the\s+day|please|now)?",
    r"inspire\s+me",
], "get_quote", 0.90)

router.register("coin_flip", [
    r"(?:flip|toss)\s+(?:a\s+)?(?:coin|quarter)",
    r"heads\s+or\s+tails",
], "flip_coin", 0.95)

router.register("dice_roll", [
    r"(?:roll|throw|toss)\s+(?:a\s+)?(?:dice|die|d\s*6)",
    r"roll\s+(?:a\s+)?(\d+)\s*(?:sided\s+)?(?:dice|die)",
], "roll_dice", 0.95, lambda t: {"sides": int(m.group(1)) if (m := re.search(r"(\d+)", t)) else 6})

# ── Math / Calculator ──
router.register("calculator", [
    r"(?:calculate|calc|compute|eval|solve|evaluate)\s+",
    r"(?:what\s+is|what'?s?)\s+\d+\s*[\+\-\*\/\%]\s*\d+",
    r"\d+\s*[\+\-\*\/\%]\s*\d+",
], "calculator", 0.90, _extract_expression)

# ── Timer ──
router.register("timer", [
    r"(?:set|start|create)\s+(?:a\s+)?timer\s+(?:for\s+)?(\d+)\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)?",
    r"timer\s+(\d+)\s*(?:seconds?|secs?|minutes?|mins?)?",
], "timer", 0.95, _extract_number)

# ── Daily Briefing ──
router.register("daily_briefing", [
    r"(?:daily\s+)?(?:briefing|schedule|what'?s?\s+on\s+my\s+schedule|what\s+do\s+i\s+have\s+today)",
], "get_daily_briefing", 0.95)

# ── Memory ──
router.register("memory_save", [
    r"(?:remember|save|store|keep)\s+(?:this|that|the\s+following)",
    r"(?:learn|memorize)\s+(?:this|that|from)",
    r"add\s+(?:this|to)\s+(?:memory|notes)",
    r"save\s+(?:this\s+)?(?:to\s+)?(?:memory|my\s+notes)",
], "memory_save_permanent", 0.90, lambda t: {"info": t, "category": "user_important"})

router.register("memory_search", [
    r"(?:what|tell\s+me)\s+(?:do\s+you\s+)?(?:remember|know|have)",
    r"search\s+(?:my\s+)?(?:memory|notes)",
    r"(?:find|show|list)\s+(?:in\s+)?(?:my\s+)?(?:memory|notes)",
    r"what\s+(?:did\s+you\s+learn|have\s+you\s+learned|do\s+you\s+know)",
], "memory_search", 0.85, lambda t: {"query": t})

# ── Todo ──
router.register("add_todo", [
    r"(?:add|create|make)\s+(?:a\s+)?(?:todo|to.?do\s+item|task|reminder)",
    r"(?:remind|reminder)\s+(?:me\s+)?(?:to|about)\s+",
    r"don'?t?\s+forget\s+(?:to|about)\s+",
], "memory_add_todo", 0.90, lambda t: {"task": t})

router.register("list_todos", [
    r"(?:list|show|get|what\s+are)\s+(?:my\s+)?(?:todos?|to.?do\s+(?:list|items|tasks)|tasks|reminders)",
    r"what\s+(?:do\s+i\s+need\s+to\s+do|is\s+on\s+my\s+list)",
], "memory_get_todos", 0.90)

# ── Notes ──
router.register("add_note", [
    r"(?:add|create|make|save|take)\s+(?:a\s+)?note",
    r"note\s+(?:this|that|down|it)",
], "memory_add_note", 0.85, lambda t: {"title": "Quick Note", "content": t})

router.register("list_notes", [
    r"(?:list|show|get|find)\s+(?:my\s+)?(?:notes|saved\s+notes)",
], "memory_search_notes", 0.85, lambda t: {"query": ""})

# ── Document ──
router.register("read_document", [
    r"(?:read|open|show)\s+(?:file|document)\s+",
    r"what'?s?\s+(?:written|in|inside)\s+(?:the\s+)?(?:file|document)",
    r"read\s+(?:the\s+)?(?:contents?\s+of\s+)?(?:this\s+)?(?:file|document)",
], "read_document", 0.90, lambda t: {"file_path": t})

# ── Shopping ──
router.register("shopping", [
    r"(?:buy|purchase|find|search|order|get)\s+(?:me\s+)?(?:a\s+|an\s+|the\s+)?(.+?)(?:\s+(?:on|from|at)\s+(?:amazon|flipkart|myntra|meesho|shopsy))",
    r"(?:cheapest|lowest\s+price|best\s+price)\s+(?:for\s+)?(.+)",
    r"compare\s+prices\s+(?:for\s+)?(.+)",
    r"(?:amazon|flipkart|myntra|shopping)\s+(?:search|find)\s+",
], "shopping_search", 0.85, lambda t: {"product": t})

# ── Fact / Info ──
router.register("random_fact", [
    r"(?:tell|give|show|get)\s+(?:me\s+)?(?:a\s+)?(?:random\s+)?(?:fact|trivia)",
    r"fact\s+(?:please|now)?",
    r"did\s+you\s+know",
], "random_fact", 0.90)

router.register("ip_lookup", [
    r"(?:what'?s?|what\s+is|find|look\s+up|trace)\s+(?:my\s+)?(?:ip|ip\s+address)",
    r"ip\s+(?:address\s+)?(?:lookup|info|geolocation)",
], "ip_lookup", 0.90)

# ── Health / Nutrition ──
router.register("nutrition", [
    r"(?:nutrition|calories?|protein|carbs?|fat|food\s+info)\s+(?:for|of|in)\s+",
    r"how\s+many\s+(?:calories|protein|carbs|fat)\s+(?:in|does|are)",
], "nutrition_info", 0.85, _extract_query)

# ── City Info ──
router.register("city_info", [
    r"(?:city|place|location)\s+(?:info|information|details)\s+(?:for|about|on)\s+",
    r"(?:tell|give)\s+(?:me\s+)?(?:about|info\s+on)\s+(?:the\s+)?(?:city|town|place)\s+",
], "city_info", 0.80, _extract_query)

# ── Email Validation ──
router.register("email_validate", [
    r"(?:validate|verify|check)\s+(?:email|e.?mail)\s+",
    r"is\s+(?:this\s+)?(?:email|e.?mail)\s+(?:address\s+)?valid",
], "email_validate", 0.85, lambda t: {"email": t})

# ── Exercise ──
router.register("exercise", [
    r"(?:exercise|workout|gym)\s+(?:for|routine|info|guide)",
    r"(?:tell|give|show)\s+(?:me\s+)?(?:exercises?|workouts?)\s+(?:for|to|about)\s+",
], "exercises", 0.85, _extract_query)

# ── Sentiment ──
router.register("sentiment", [
    r"(?:sentiment|sentiment\s+analysis|mood)\s+(?:of|analyze|analysis|check)",
    r"analyze\s+(?:the\s+)?(?:sentiment|mood|tone|emotion)",
], "sentiment_analysis", 0.80, _extract_query)

# ── Holiday ──
router.register("holidays", [
    r"(?:holidays?|festivals?|events)\s+(?:in|for|on)\s+",
    r"list\s+(?:holidays?|festivals?)\s+",
    r"(?:national|public)\s+(?:holidays?)\s+",
], "global_holidays", 0.85, lambda t: {"country_code": "IN"})

# ── Web Browser ──
router.register("web_visit", [
    r"(?:visit|open|navigate\s+to|browse)\s+(?:the\s+)?(?:page|website|site|webpage)\s+",
    r"(?:visit|open|navigate\s+to|go\s+to)\s+https?://",
], "open_app", 0.90, _extract_url_or_query)

# ── Window Control ──
router.register("window_control", [
    r"(?:minimize|maximize|restore|close|focus)\s+(?:the\s+)?(?:window|app|application)\s+",
    r"switch\s+(?:to|window)\s+",
    r"show\s+(?:desktop|all\s+windows)",
], "window_control", 0.85, lambda t: {"action": "minimize" if "minimize" in t else "maximize" if "maximize" in t else "close" if "close" in t else "focus" if "focus" in t else "switch" if "switch" in t else "list" if "list" in t or "show" in t else "minimize", "title": t})

# ── Screen Info ──
router.register("screen_info", [
    r"(?:screen|display|monitor)\s+(?:resolution|info|information|size|details)",
    r"(?:what'?s?|what\s+is|get)\s+(?:my\s+)?(?:screen|display)\s+(?:resolution|size)",
], "get_screen_info", 0.90)

# ── Network Speed ──
router.register("speed_test", [
    r"(?:network|internet)\s+(?:speed|test|speedtest|performance)",
    r"(?:run|do|check)\s+(?:a\s+)?(?:network|internet)\s+(?:speed|test)",
    r"speed\s+test",
], "run_network_speed_test", 0.85)

# ── Keyboard Type ──
router.register("type_text", [
    r"(?:type|write|enter)\s+(?:the\s+)?(?:text|word|words|sentence)\s+",
    r"type\s+['\"]?(.+?)['\"]?$",
], "type_text", 0.85, lambda t: {"text": t})

# ── Mouse Control ──
router.register("mouse_control", [
    r"(?:move|click|double.?click|right.?click)\s+(?:the\s+)?mouse\s+",
    r"mouse\s+(?:move|click|position)",
], "mouse_control", 0.80, lambda t: {"action": "click" if "click" in t else "move" if "move" in t else "click", "x": 0, "y": 0})

# ── Music (Spotify) ──
router.register("play_music", [
    r"play\s+(?:music|song|audio)\s+",
    r"play\s+.+\s+(?:song|music|track|audio|gaana)",
    r"play\s+.+\s+on\s+(?:spotify|music|gaana|wynk|jiosaavn)",
], "play_music", 0.90, _extract_query)

# ── Datetime ──
router.register("datetime", [
    r"(?:what'?s?|what\s+is|tell\s+me)\s+(?:the\s+)?(?:time|date|day)",
    r"(?:current|today'?s?)\s+(?:time|date|day)",
    r"(?:what|which)\s+(?:day|date|time)\s+is\s+(?:it|today)",
], "get_datetime", 0.95)

# ── Plot Chart ──
router.register("plot_chart", [
    r"(?:plot|draw|create|make|show)\s+(?:a\s+)?(?:chart|graph|plot)",
    r"(?:bar|line|pie)\s+(?:chart|graph|plot)",
], "plot_chart", 0.80, lambda t: {"chart_type": "bar" if "bar" in t else "line" if "line" in t else "pie" if "pie" in t else "bar", "title": t, "labels": [], "values": []})


def route_input(text: str) -> ToolAction | None:
    return router.route(text)


def execute_tool(action: ToolAction) -> Any:
    """Execute a tool action and return either plain text or a structured payload."""
    from jarvis import tools as jarvis_tools
    from jarvis.system_control import (
        volume_control,
        brightness_control,
        window_control,
        system_power,
        screenshot,
        clipboard_manager,
        type_text,
        mouse_control,
        get_screen_info,
    )
    from jarvis.dashboard import (
        get_system_stats,
        get_quick_system_status,
        run_network_speed_test,
    )
    from jarvis.memory import (
        memory_add_todo,
        memory_get_todos,
        memory_add_note,
        memory_search_notes,
        memory_save_permanent,
        memory_get_briefing,
    )

    handler_map: dict[str, Callable[..., Any]] = {
        # YouTube
        "search_youtube": jarvis_tools.search_youtube,
        "play_youtube": jarvis_tools.play_youtube,
        "play_music": jarvis_tools.play_music,
        # Web
        "open_app": jarvis_tools.open_app,
        "web_search": jarvis_tools.web_search,
        # Weather
        "get_weather": jarvis_tools.get_weather,
        # News
        "finnhub_market_news": jarvis_tools.finnhub_market_news,
        # NASA
        "nasa_apod": jarvis_tools.nasa_apod,
        "nasa_mars_rover": jarvis_tools.nasa_mars_rover,
        "nasa_iss": jarvis_tools.nasa_iss,
        "nasa_space_data": jarvis_tools.nasa_space_data,
        # Stocks
        "finnhub_quote": jarvis_tools.finnhub_quote,
        # System
        "get_system_stats": get_system_stats,
        "volume_control": volume_control,
        "screenshot": screenshot,
        "clipboard_manager": clipboard_manager,
        "brightness_control": brightness_control,
        "window_control": window_control,
        "system_power": system_power,
        "type_text": type_text,
        "mouse_control": mouse_control,
        "get_screen_info": get_screen_info,
        "run_network_speed_test": run_network_speed_test,
        # Entertainment
        "get_joke": jarvis_tools.get_joke,
        "get_quote": jarvis_tools.get_quote,
        "flip_coin": jarvis_tools.flip_coin,
        "roll_dice": jarvis_tools.roll_dice,
        # Tools
        "calculator": jarvis_tools.calculator,
        "timer": jarvis_tools.timer,
        "get_datetime": jarvis_tools.get_datetime,
        "random_fact": jarvis_tools.random_fact,
        "ip_lookup": jarvis_tools.ip_lookup,
        "nutrition_info": jarvis_tools.nutrition_info,
        "city_info": jarvis_tools.city_info,
        "email_validate": jarvis_tools.email_validate,
        "exercises": jarvis_tools.exercises,
        "sentiment_analysis": jarvis_tools.sentiment_analysis,
        "global_holidays": jarvis_tools.global_holidays,
        "close_app": jarvis_tools.close_app,
        "list_running_apps": jarvis_tools.list_running_apps,
        "plot_chart": jarvis_tools.plot_chart,
        # Memory / Todo / Notes
        "memory_add_todo": memory_add_todo,
        "memory_get_todos": memory_get_todos,
        "memory_add_note": memory_add_note,
        "memory_search_notes": memory_search_notes,
        "memory_save_permanent": memory_save_permanent,
        "get_daily_briefing": memory_get_briefing,
    }

    handler = handler_map.get(action.handler)
    if not handler:
        return f"Tool '{action.handler}' not found."

    try:
        result = handler(**action.params)

        if isinstance(result, dict):
            if "response" in result or "actions" in result or "suggestions" in result:
                return result
            if "text" in result and isinstance(result["text"], str):
                return {"response": result["text"], "actions": []}

        if isinstance(result, list):
            return {
                "response": ", ".join(str(item) for item in result),
                "actions": [],
            }

        return str(result)
    except Exception as e:
        logger.warning("Tool '%s' failed: %s", action.handler, e)
        return f"I tried to {action.name} but ran into an issue: {e}"


tool_router = router
