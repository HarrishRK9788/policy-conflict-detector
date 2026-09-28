"""
polarity.py
-----------
Detects the obligation polarity of a policy sentence.

Polarity values:
    "POSITIVE" -> sentence mandates/requires an action (must, shall, required, should)
    "NEGATIVE" -> sentence forbids an action (must not, may not, prohibited, shall not,
                  cannot, is not permitted, is forbidden)
    "NONE"     -> sentence carries no clear obligation polarity

Order matters: negative patterns are checked BEFORE positive ones because a
negative pattern like "must not" contains the positive keyword "must".
"""

import re
from typing import Literal

Polarity = Literal["POSITIVE", "NEGATIVE", "NONE"]

# Negative patterns are checked first (most specific / longest match first).
_NEGATIVE_PATTERNS = [
    r"\bmust\s+not\b",
    r"\bshall\s+not\b",
    r"\bmay\s+not\b",
    r"\bshould\s+not\b",
    r"\bcannot\b",
    r"\bcan\s*not\b",
    r"\bis\s+not\s+permitted\b",
    r"\bare\s+not\s+permitted\b",
    r"\bis\s+forbidden\b",
    r"\bis\s+prohibited\b",
    r"\bare\s+prohibited\b",
    r"\bprohibited\b",
    r"\bnot\s+allowed\b",
    r"\bnever\b",
]

_POSITIVE_PATTERNS = [
    r"\bmust\b",
    r"\bshall\b",
    r"\bis\s+required\s+to\b",
    r"\bare\s+required\s+to\b",
    r"\brequired\b",
    r"\bshould\b",
    r"\bwill\b",
    r"\bis\s+mandatory\b",
]

_NEGATIVE_RE = re.compile("|".join(_NEGATIVE_PATTERNS), re.IGNORECASE)
_POSITIVE_RE = re.compile("|".join(_POSITIVE_PATTERNS), re.IGNORECASE)


def detect_polarity(sentence: str) -> Polarity:
    """Determine the obligation polarity of a single sentence.

    Args:
        sentence: The raw sentence text.

    Returns:
        "POSITIVE", "NEGATIVE", or "NONE".
    """
    if not sentence or not sentence.strip():
        return "NONE"

    if _NEGATIVE_RE.search(sentence):
        return "NEGATIVE"
    if _POSITIVE_RE.search(sentence):
        return "POSITIVE"
    return "NONE"


def polarity_label(polarity: Polarity) -> str:
    """Human friendly label for a polarity value, used in the UI."""
    mapping = {
        "POSITIVE": "Required",
        "NEGATIVE": "Prohibited",
        "NONE": "Informational",
    }
    return mapping.get(polarity, "Informational")
