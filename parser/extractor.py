"""
extractor.py
------------
Splits raw policy body text into sentences and identifies which sentences
are "obligation sentences" (i.e. sentences that impose a rule using
words such as must, shall, required, should, must not, may not, prohibited).

Sentence segmentation is performed with spaCy when the `en_core_web_sm`
model is available (for higher accuracy on abbreviations, decimals such as
"TLS 1.0", etc). If the model cannot be loaded (e.g. offline environment
without the model downloaded yet), a robust regex-based sentence splitter
is used as an automatic fallback so the application never crashes.
"""

import re
from typing import List

_NLP = None
_SPACY_AVAILABLE = False

try:
    import spacy

    try:
        _NLP = spacy.load("en_core_web_sm")
        _SPACY_AVAILABLE = True
    except OSError:
        # Model not downloaded yet -- fall back to blank pipeline w/ sentencizer.
        try:
            _NLP = spacy.blank("en")
            _NLP.add_pipe("sentencizer")
            _SPACY_AVAILABLE = True
        except Exception:
            _NLP = None
            _SPACY_AVAILABLE = False
except ImportError:
    _NLP = None
    _SPACY_AVAILABLE = False


# Obligation keywords per the spec: must, shall, required, must not, may not,
# prohibited, should (and their common negative counterparts).
OBLIGATION_KEYWORDS = [
    "must not", "may not", "shall not", "should not", "cannot", "can not",
    "prohibited", "forbidden", "not permitted", "not allowed",
    "must", "shall", "required", "should", "mandatory",
]

_OBLIGATION_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in OBLIGATION_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Fallback sentence splitter: split on '.', '!', '?' followed by whitespace and
# a capital letter, but avoid breaking on common abbreviations/decimals like
# "TLS 1.0" or "v1.2" by requiring at least one space after the punctuation.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def split_sentences(text: str) -> List[str]:
    """Split a block of text into cleaned sentences.

    Args:
        text: Raw multi-sentence text (the body of a policy document).

    Returns:
        List of non-empty, stripped sentence strings.
    """
    text = text.strip()
    if not text:
        return []

    if _SPACY_AVAILABLE and _NLP is not None:
        try:
            doc = _NLP(text)
            sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
            if sentences:
                return sentences
        except Exception:
            pass  # fall through to regex splitter

    # Regex fallback
    raw_sentences = _SENTENCE_SPLIT_RE.split(text)
    return [s.strip() for s in raw_sentences if s.strip()]


def is_obligation_sentence(sentence: str) -> bool:
    """Return True if the sentence contains an obligation/prohibition keyword."""
    return bool(_OBLIGATION_RE.search(sentence))


def extract_obligation_sentences(text: str) -> List[str]:
    """Extract only the sentences from `text` that express an obligation.

    Args:
        text: Raw policy body text.

    Returns:
        List of sentences that contain obligation language (must, shall,
        required, should, must not, may not, prohibited, etc).
    """
    sentences = split_sentences(text)
    return [s for s in sentences if is_obligation_sentence(s)]
