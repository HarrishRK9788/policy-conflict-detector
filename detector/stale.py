"""
stale.py
--------
Detects stale / outdated policy documents.

A policy document is flagged as stale if either:
    1. Its "Last Reviewed" date is more than 18 months before the current
       date (or the date is missing entirely), OR
    2. Its text references a known deprecated technology, such as:
       TLS 1.0, SSL, SHA-1, MD5, Windows Server 2012, Windows Server 2008
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from parser.parser import PolicyDocument

STALE_THRESHOLD_MONTHS = 18

DEPRECATED_TECHNOLOGIES = [
    "TLS 1.0",
    "TLS1.0",
    "SSL",
    "SHA-1",
    "SHA1",
    "MD5",
    "Windows Server 2012",
    "Windows Server 2008",
]

_DEPRECATED_RE = re.compile(
    r"|".join(re.escape(t) for t in DEPRECATED_TECHNOLOGIES),
    re.IGNORECASE,
)


@dataclass
class StaleFinding:
    """Represents a staleness finding for one policy document."""

    document_title: str
    source_file: str
    last_reviewed: Optional[datetime]
    months_since_review: Optional[int]
    is_age_stale: bool
    deprecated_tech_found: List[str] = field(default_factory=list)

    @property
    def is_stale(self) -> bool:
        return self.is_age_stale or bool(self.deprecated_tech_found)

    @property
    def reasons(self) -> List[str]:
        reasons = []
        if self.is_age_stale:
            if self.last_reviewed is None:
                reasons.append("No 'Last Reviewed' date found in document")
            else:
                reasons.append(
                    f"Not reviewed in {self.months_since_review} months "
                    f"(threshold: {STALE_THRESHOLD_MONTHS} months)"
                )
        for tech in self.deprecated_tech_found:
            reasons.append(f"References deprecated technology: {tech}")
        return reasons

    def to_dict(self) -> dict:
        return {
            "document_title": self.document_title,
            "source_file": self.source_file,
            "last_reviewed": self.last_reviewed.strftime("%Y-%m-%d") if self.last_reviewed else None,
            "months_since_review": self.months_since_review,
            "is_age_stale": self.is_age_stale,
            "deprecated_tech_found": self.deprecated_tech_found,
            "is_stale": self.is_stale,
            "reasons": self.reasons,
        }


def _find_deprecated_technologies(text: str) -> List[str]:
    matches = _DEPRECATED_RE.findall(text)
    # Normalize casing / dedupe while preserving a canonical display form.
    canonical = []
    seen = set()
    for m in matches:
        key = m.upper().replace(" ", "")
        if key not in seen:
            seen.add(key)
            canonical.append(m)
    return canonical


def detect_staleness(
    document: PolicyDocument,
    reference_date: Optional[datetime] = None,
) -> StaleFinding:
    """Evaluate a single PolicyDocument for staleness.

    Args:
        document: The parsed PolicyDocument.
        reference_date: The "current" date to compare against (defaults to
            now). Exposed as a parameter for testability.

    Returns:
        A StaleFinding describing the result.
    """
    reference_date = reference_date or datetime.now()

    months_since_review: Optional[int] = None
    is_age_stale = False

    if document.last_reviewed is None:
        is_age_stale = True
    else:
        delta = relativedelta(reference_date, document.last_reviewed)
        months_since_review = delta.years * 12 + delta.months
        if months_since_review >= STALE_THRESHOLD_MONTHS:
            is_age_stale = True

    deprecated_found = _find_deprecated_technologies(document.raw_text)

    return StaleFinding(
        document_title=document.title,
        source_file=document.filename,
        last_reviewed=document.last_reviewed,
        months_since_review=months_since_review,
        is_age_stale=is_age_stale,
        deprecated_tech_found=deprecated_found,
    )


def detect_all_staleness(
    documents: List[PolicyDocument],
    reference_date: Optional[datetime] = None,
) -> List[StaleFinding]:
    """Run staleness detection across every parsed document."""
    return [detect_staleness(doc, reference_date) for doc in documents]
