"""
conflict.py
-----------
Detects conflicting policy statements.

Rule: two statements conflict if and only if:
    1. They share the same topic (e.g. both PASSWORD)
    2. They share the same action (e.g. both "rotate")
    3. Their polarity is opposite (one POSITIVE, one NEGATIVE)

Example:
    "Passwords must be rotated every 90 days."       -> PASSWORD / rotate / POSITIVE
    "Passwords must not be rotated more than yearly." -> PASSWORD / rotate / NEGATIVE
    => CONFLICT
"""

from dataclasses import dataclass
from itertools import combinations
from typing import List

from parser.parser import Statement


@dataclass
class Conflict:
    """Represents a detected conflict between two statements."""

    statement_a: Statement
    statement_b: Statement
    topic: str
    action: str
    severity: str  # "HIGH" | "MEDIUM"

    def to_dict(self) -> dict:
        return {
            "statement_a": self.statement_a.to_dict(),
            "statement_b": self.statement_b.to_dict(),
            "topic": self.topic,
            "action": self.action,
            "severity": self.severity,
        }


def _severity(a: Statement, b: Statement) -> str:
    """Conflicts between statements from *different* source files are more
    severe (cross-document policy contradictions) than conflicts within the
    same document (which usually indicate an internal drafting error but
    affect a narrower blast radius in practice)."""
    return "HIGH" if a.source_file != b.source_file else "MEDIUM"


def detect_conflicts(statements: List[Statement]) -> List[Conflict]:
    """Find all pairs of statements that conflict with each other.

    Args:
        statements: Flat list of Statement objects across all parsed
            policy documents.

    Returns:
        List of Conflict objects.
    """
    conflicts: List[Conflict] = []

    # Only compare statements that actually have both a topic and an action,
    # since conflict detection requires exact topic+action matches.
    comparable = [
        s for s in statements
        if s.action is not None and s.topic != "GENERAL" and s.polarity in ("POSITIVE", "NEGATIVE")
    ]

    for a, b in combinations(comparable, 2):
        if a.id == b.id:
            continue
        if a.topic != b.topic:
            continue
        if a.action != b.action:
            continue
        if a.polarity == b.polarity:
            continue  # same polarity -> not a conflict (may be redundant)
        if a.polarity == "NONE" or b.polarity == "NONE":
            continue

        conflicts.append(
            Conflict(
                statement_a=a,
                statement_b=b,
                topic=a.topic,
                action=a.action,
                severity=_severity(a, b),
            )
        )

    return conflicts
