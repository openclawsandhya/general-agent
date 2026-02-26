"""
Intent router to classify user messages as chat or automation.
"""

import re
from typing import Tuple
from models.schemas import IntentType
from .utils.logger import get_logger


logger = get_logger(__name__)


class IntentRouter:
    """Routes user messages to appropriate handler based on intent."""
    
    # Action keywords that indicate browser automation request
    AUTOMATION_KEYWORDS = {
        "open", "visit", "go to", "navigate", "search", "find", "look for",
        "click", "press", "scroll", "extract", "read", "get", "fetch",
        "type", "enter", "fill", "submit", "screenshot", "capture",
        "download", "upload", "drag", "drop", "hover", "wait for",
        "load", "browse", "check", "verify", "follow", "access", "reach"
    }
    
    # Patterns that match automation requests
    AUTOMATION_PATTERNS = [
        r"(?:open|visit|go to|navigate to)\s+(?:the\s+)?(?:website|page|url|site|link)",
        r"(?:search|look for|find|search for)\s+(?:.*)?",
        r"(?:click|press|select)\s+(?:on\s+)?(?:the\s+)?(?:button|link|element)",
        r"(?:scroll|go|navigate)\s+(?:up|down|back|forward|left|right)",
        r"(?:extract|read|get|retrieve|download)\s+(?:the\s+)?(?:text|content|data|information)",
        r"(?:type|enter|fill|input)\s+(?:.*)\s+(?:in|into|on)\s+(?:.*)",
        r"(?:can you|please|pls)?\s*(?:open|search|find|click|scroll|browse|check|extract)",
    ]
    
    def __init__(self):
        """Initialize intent router."""
        logger.info("IntentRouter initialized")
    
    def route(self, message: str) -> Tuple[IntentType, float]:
        """
        Classify user message intent.
        
        Args:
            message: User message
            
        Returns:
            Tuple of (intent_type, confidence_score)
        """
        message_lower = message.lower().strip()
        
        # Check for automation patterns
        confidence = self._calculate_confidence(message_lower)
        
        if confidence > 0.3:
            intent = IntentType.AUTOMATION
        else:
            intent = IntentType.CHAT
        
        logger.debug(
            f"Routed message to {intent.value} "
            f"(confidence: {confidence:.2f})"
        )
        
        return intent, confidence
    
    def _calculate_confidence(self, message: str) -> float:
        """
        Calculate confidence that message is automation request.
        
        Args:
            message: Lowercase message text
            
        Returns:
            Confidence score (0.0-1.0)
        """
        score = 0.0
        
        # Check for automation keywords
        keyword_matches = sum(
            1 for keyword in self.AUTOMATION_KEYWORDS
            if f" {keyword} " in f" {message} "
        )
        keyword_score = min(keyword_matches * 0.15, 0.6)
        score += keyword_score
        
        # Check for URL patterns
        if self._contains_url_pattern(message):
            score += 0.2
        
        # Check for regex patterns
        for pattern in self.AUTOMATION_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                score += 0.3
                break
        
        # Normalize score
        return min(score, 1.0)
    
    def _contains_url_pattern(self, message: str) -> bool:
        """Check if message contains URL patterns."""
        url_pattern = r'(?:https?://|www\.|\.com|\.org|\.net)'
        return bool(re.search(url_pattern, message, re.IGNORECASE))
