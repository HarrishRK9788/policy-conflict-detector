"""
parser.py
---------
Top level parsing module. Converts a raw uploaded .txt policy document into
a structured PolicyDocument containing a list of Statement objects.

Expected (loosely enforced) document format::

    Title: Password Policy
    Last Reviewed: 2022-01-15

    All passwords must be rotated every 90 days.
    Passwords must not be shared with any third party.
    ...

If a "Title:" line is missing, the filename (without extension) is used.
If a "Last Reviewed:" line is missing or unparsable, the document is
treated as having an unknown review date (flagged in the UI, but not
counted as stale by age -- it can still be flagged for deprecated tech).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from dateutil import parser as dateutil_parser

from parser.extractor import split_sentences, is_obligation_sentence
from parser.classifier import classify_topic
from parser.action_extractor import extract_action
from parser.polarity import detect_polarity

_TITLE_RE = re.compile(r"^\s*Title\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_REVIEWED_RE = re.compile(r"^\s*Last\s*Reviewed\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


@dataclass
class Statement:
    """A single obligation statement extracted from a policy document."""

    id: str
    policy_title: str
    source_file: str
    text: str
    topic: str
    action: Optional[str]
    polarity: str  # "POSITIVE" | "NEGATIVE" | "NONE"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "policy_title": self.policy_title,
            "source_file": self.source_file,
            "text": self.text,
            "topic": self.topic,
            "action": self.action,
            "polarity": self.polarity,
        }


@dataclass
class PolicyDocument:
    """A fully parsed policy document."""

    filename: str
    title: str
    last_reviewed: Optional[datetime]
    raw_text: str
    statements: List[Statement] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "title": self.title,
            "last_reviewed": self.last_reviewed.strftime("%Y-%m-%d") if self.last_reviewed else None,
            "statement_count": len(self.statements),
            "statements": [s.to_dict() for s in self.statements],
        }


def _extract_title(text: str, fallback: str) -> str:
    match = _TITLE_RE.search(text)
    if match:
        return match.group(1).strip()
    return fallback


def _extract_last_reviewed(text: str) -> Optional[datetime]:
    match = _REVIEWED_RE.search(text)
    if not match:
        return None
    raw_date = match.group(1).strip()
    try:
        return dateutil_parser.parse(raw_date, fuzzy=True)
    except (ValueError, OverflowError):
        return None


def _strip_header(text: str) -> str:
    """Remove the Title: / Last Reviewed: header lines, returning the body."""
    body = _TITLE_RE.sub("", text)
    body = _REVIEWED_RE.sub("", body)
    return body.strip()


def parse_policy_document(filename: str, raw_text: str) -> PolicyDocument:
    """Parse a single raw policy .txt file's contents into a PolicyDocument.

    Args:
        filename: Original uploaded filename (used as fallback title source
            and as the `source_file` identifier for statements).
        raw_text: The full raw text content of the file.

    Returns:
        A populated PolicyDocument, including its list of Statement objects
        (only sentences that express an obligation are kept as statements).
    """
    fallback_title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    title = _extract_title(raw_text, fallback_title)
    last_reviewed = _extract_last_reviewed(raw_text)
    body = _strip_header(raw_text)

    sentences = split_sentences(body)

    statements: List[Statement] = []
    for idx, sentence in enumerate(sentences):
        if not is_obligation_sentence(sentence):
            continue
        topic = classify_topic(sentence)
        action = extract_action(sentence)
        polarity = detect_polarity(sentence)

        statements.append(
            Statement(
                id=f"{filename}::{idx}",
                policy_title=title,
                source_file=filename,
                text=sentence,
                topic=topic,
                action=action,
                polarity=polarity,
            )
        )

    return PolicyDocument(
        filename=filename,
        title=title,
        last_reviewed=last_reviewed,
        raw_text=raw_text,
        statements=statements,
    )


def parse_multiple(files: dict) -> List[PolicyDocument]:
    """Parse multiple uploaded files.

    Args:
        files: Mapping of filename -> raw text content.

    Returns:
        List of PolicyDocument objects, one per input file.
    """
    return [parse_policy_document(fname, text) for fname, text in files.items()]
