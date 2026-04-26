"""jarvis.intent_classifier

Advanced NLP intent classification for JARVIS.
Determines when to save to memory, learn from content, or execute commands.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """Types of user intents."""
    LEARN_CONTENT = "learn_content"  # Learn from content
    SAVE_MEMORY = "save_memory"      # Save to memory explicitly
    CHAT = "chat"                    # Regular chat
    COMMAND = "command"              # Execute command
    FILE_ANALYSIS = "file_analysis"  # Analyze file
    YOUTUBE_LEARN = "youtube_learn"  # Learn from YouTube
    WEB_SEARCH = "web_search"        # Search web page
    SHOPPING = "shopping"            # Shopping query
    MULTITASK = "multitask"          # Background task
    QUESTION = "question"            # Question answering


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent: IntentType
    confidence: float
    extracted_data: Dict
    should_learn: bool
    should_save: bool


class IntentClassifier:
    """Advanced intent classifier for JARVIS."""
    
    def __init__(self):
        self.learning_patterns = [
            r"learn\s+(?:this|from|about)",
            r"save\s+(?:this|to\s+memory)",
            r"remember\s+(?:this|that)",
            r"add\s+(?:this|to)\s+(?:memory|notes)",
            r"store\s+(?:this|in)",
            r"keep\s+this",
            r"analyze\s+and\s+save",
            r"learn\s+from\s+this",
            r"make\s+notes\s+(?:of|on|about)",
            r"create\s+notes",
            r"summarize\s+and\s+save",
            r"study\s+(?:this|from)",
        ]
        
        self.youtube_patterns = [
            r"learn\s+from\s+(?:this|youtube|video)",
            r"watch\s+and\s+learn",
            r"analyze\s+video",
            r"study\s+video",
            r"youtube\.com/watch",
            r"youtu\.be/",
            r"learn\s+from\s+youtube",
        ]
        
        self.web_search_patterns = [
            r"search\s+(?:web|internet|page|site)",
            r"find\s+(?:on|from)\s+(?:web|internet|page)",
            r"look\s+up\s+(?:on|in)",
            r"visit\s+page",
            r"browse\s+(?:to|site)",
            r"scrape\s+(?:page|site)",
            r"extract\s+(?:from|info)",
        ]
        
        self.shopping_patterns = [
            r"(?:find|search|buy|purchase|get)\s+(?:me\s+)?(?:(?:a|an|the)\s+)?(.+?)(?:\s+(?:on|from|at)\s+)?",
            r"(?:cheapest|lowest\s+price|best\s+price)",
            r"compare\s+prices",
            r"shopping",
            r"amazon|flipkart|myntra|meesho|shopsy",
        ]
        
        self.multitask_patterns = [
            r"(?:do\s+this\s+in\s+background|run\s+in\s+background)",
            r"(?:continue\s+this|do\s+this\s+later)",
            r"(?:while\s+you.*do\s+this|while\s+i.*do\s+that)",
        ]
        
        self.command_patterns = [
            r"^(open|close|launch|start|stop|restart|shutdown|reboot|lock|sleep|logout)",
            r"^(play|pause|stop|next|previous|volume)",
            r"^(search|find|locate)",
            r"^(create|make|new)",
            r"^(delete|remove|trash)",
            r"^(copy|paste|cut|move)",
        ]
        
        self.question_patterns = [
            r"^(what|who|where|when|why|how|which|whose|whom)",
            r"\?$",
            r"^(is|are|was|were|do|does|did|can|could|will|would|should|shall|may|might|must|have|has|had)",
        ]
    
    def classify(self, user_input: str) -> IntentResult:
        """Classify user intent with confidence score."""
        text = user_input.lower().strip()
        
        # Check for YouTube learning first
        if self._matches_patterns(text, self.youtube_patterns):
            return IntentResult(
                intent=IntentType.YOUTUBE_LEARN,
                confidence=0.9,
                extracted_data={"url": self._extract_url(text)},
                should_learn=True,
                should_save=True
            )
        
        # Check for web search
        if self._matches_patterns(text, self.web_search_patterns):
            return IntentResult(
                intent=IntentType.WEB_SEARCH,
                confidence=0.85,
                extracted_data={"url": self._extract_url(text), "query": self._extract_query(text)},
                should_learn=False,
                should_save=False
            )
        
        # Check for shopping
        if self._matches_patterns(text, self.shopping_patterns):
            return IntentResult(
                intent=IntentType.SHOPPING,
                confidence=0.8,
                extracted_data={"product": self._extract_product(text)},
                should_learn=False,
                should_save=False
            )
        
        # Check for multitasking
        if self._matches_patterns(text, self.multitask_patterns):
            return IntentResult(
                intent=IntentType.MULTITASK,
                confidence=0.85,
                extracted_data={},
                should_learn=False,
                should_save=False
            )
        
        # Check for explicit learning/saving
        if self._matches_patterns(text, self.learning_patterns):
            return IntentResult(
                intent=IntentType.LEARN_CONTENT,
                confidence=0.9,
                extracted_data={"content": text},
                should_learn=True,
                should_save=True
            )
        
        # Check for file analysis with learning
        if any(word in text for word in ["file", "document", "pdf", "read"]):
            should_learn = self._matches_patterns(text, self.learning_patterns)
            return IntentResult(
                intent=IntentType.FILE_ANALYSIS,
                confidence=0.75,
                extracted_data={},
                should_learn=should_learn,
                should_save=should_learn
            )
        
        # Check for commands
        if self._matches_patterns(text, self.command_patterns):
            return IntentResult(
                intent=IntentType.COMMAND,
                confidence=0.8,
                extracted_data={"command": text},
                should_learn=False,
                should_save=False
            )
        
        # Check for questions
        if self._matches_patterns(text, self.question_patterns):
            return IntentResult(
                intent=IntentType.QUESTION,
                confidence=0.7,
                extracted_data={"question": text},
                should_learn=False,
                should_save=False
            )
        
        # Default to chat
        return IntentResult(
            intent=IntentType.CHAT,
            confidence=0.6,
            extracted_data={},
            should_learn=False,
            should_save=False
        )
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the patterns."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text."""
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
        match = re.search(url_pattern, text)
        return match.group(0) if match else None
    
    def _extract_query(self, text: str) -> str:
        """Extract search query from text."""
        # Remove common words and extract the actual query
        stop_words = ["search", "web", "internet", "page", "site", "for", "about", "on", "in"]
        words = text.lower().split()
        query_words = [w for w in words if w not in stop_words]
        return " ".join(query_words) if query_words else text
    
    def _extract_product(self, text: str) -> str:
        """Extract product name from shopping query."""
        # Try to extract product after "buy", "purchase", "find"
        patterns = [
            r'(?:buy|purchase|find|get|search)\s+(?:me\s+)?(?:a|an|the)?\s*(.+?)(?:\s+(?:on|from|at|with|under|below)|\s+\d|$)',
            r'(?:cheapest|lowest\s+price|best\s+price)?\s*(.+?)(?:\s+(?:on|from|at)|\s*$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return text
    
    def should_learn_from_content(self, user_input: str) -> bool:
        """Quick check if user wants to learn/save content."""
        result = self.classify(user_input)
        return result.should_learn
    
    def should_save_to_memory(self, user_input: str) -> bool:
        """Quick check if content should be saved to memory."""
        result = self.classify(user_input)
        return result.should_save


# Global instance
intent_classifier = IntentClassifier()


def classify_intent(user_input: str) -> IntentResult:
    """Classify user intent."""
    return intent_classifier.classify(user_input)


def should_learn(user_input: str) -> bool:
    """Check if user wants to learn from content."""
    return intent_classifier.should_learn_from_content(user_input)


def should_save(user_input: str) -> bool:
    """Check if content should be saved."""
    return intent_classifier.should_save_to_memory(user_input)


# Tool functions for LLM
def tool_classify_intent(text: str) -> str:
    """Tool: Classify intent of user message."""
    result = classify_intent(text)
    return f"Intent: {result.intent.value}, Confidence: {result.confidence:.2f}, Learn: {result.should_learn}"


def tool_should_learn(text: str) -> str:
    """Tool: Check if should learn from content."""
    return "Yes" if should_learn(text) else "No"


INTENT_REGISTRY = {
    "intent_classify": tool_classify_intent,
    "intent_should_learn": tool_should_learn,
}
