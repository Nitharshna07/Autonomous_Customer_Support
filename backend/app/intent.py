import re
from typing import Tuple

INTENT_KEYWORDS = {
    "urgent": [
        "urgent", "immediately", "emergency", "asap", "critical", "broken completely",
        "down", "outage", "system down", "cannot access", "security breach", "hacked"
    ],
    "complaint": [
        "angry", "frustrated", "terrible", "horrible", "awful", "scam", "lawsuit",
        "sue", "unacceptable", "disappointed", "refund immediately", "worst service",
        "ridiculous", "fail", "complaint", "waste of money"
    ],
    "billing": [
        "invoice", "billing", "bill", "payment", "charge", "charged", "credit card",
        "subscription", "price", "pricing", "refund", "receipt", "tier", "plan"
    ],
    "technical": [
        "bug", "error", "issue", "crash", "stack trace", "exception", "failed",
        "code", "api", "endpoint", "slow", "performance", "404", "500", "loading"
    ],
    "account": [
        "password", "login", "signup", "register", "profile", "settings",
        "email", "auth", "2fa", "mfa", "reset password", "account", "deactivate"
    ]
}

HIGH_PRIORITY_INTENTS = {"urgent", "complaint"}

def classify_intent(text: str) -> Tuple[str, float]:
    """
    Classify user message into an intent category and compute confidence score.
    Returns (intent_name, confidence_score).
    """
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    total_words = max(len(words), 1)

    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        match_count = 0
        for kw in keywords:
            if kw in text_lower:
                match_count += 1
        if match_count > 0:
            # Score scaled by number of keyword matches and string density
            scores[intent] = match_count

    if not scores:
        return "general", 0.65

    best_intent = max(scores, key=scores.get)
    best_matches = scores[best_intent]

    # Calculate confidence based on matches relative to word length
    if best_matches >= 3:
        confidence = 0.95
    elif best_matches == 2:
        confidence = 0.85
    else:
        confidence = 0.72

    return best_intent, round(confidence, 2)

def detect_anger_frustration(text: str) -> bool:
    """
    Detect user anger or frustration based on keywords and capitalization indicators.
    """
    text_lower = text.lower()
    anger_keywords = [
        "angry", "frustrated", "annoyed", "pissed", "mad", "hate", "scam", "useless",
        "crap", "terrible", "horrible", "awful", "worst", "unacceptable", "sue", "lawsuit",
        "disappointed", "ridiculous", "refund immediately", "waste of money", "waste of time"
    ]
    if any(kw in text_lower for kw in anger_keywords):
        return True
    
    # Check for all-caps expressions containing substantial words (e.g. "I WANT A REFUND NOW")
    words = re.findall(r'\b[A-Z]+\b', text)
    if len(words) >= 3 and len(text) > 10:
        all_caps_words = [w for w in words if len(w) > 1]
        if len(all_caps_words) >= 3:
            return True
            
    return False

def should_escalate(
    intent: str,
    intent_confidence: float,
    rag_score: float,
    rag_threshold: float,
    has_kb_docs: bool,
    is_angry: bool = False
) -> Tuple[bool, str]:
    """
    Determine if conversation should auto-escalate to human agent.
    Returns (is_escalated, escalation_reason).
    """
    if intent in HIGH_PRIORITY_INTENTS:
        return True, f"High priority customer intent detected ({intent.upper()})"

    if is_angry:
        return True, "Frustrated or angry customer sentiment detected"

    if intent == "general":
        # General conversational chats/greetings don't need RAG grounding or escalation on low RAG score
        return False, ""

    if has_kb_docs and rag_score < rag_threshold:
        return True, f"Low RAG knowledge base retrieval confidence ({rag_score:.2f} < threshold {rag_threshold})"

    return False, ""
