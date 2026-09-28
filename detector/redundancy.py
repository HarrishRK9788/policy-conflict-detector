"""
redundancy.py
-------------
Detects redundant policy statements.

Rule: two statements are redundant if and only if:
    1. They share the same topic
    2. They share the same action
    3. They share the same polarity
    4. They come from different statements (and ideally different source
       documents, which is the more actionable/interesting case for
       consolidation)
"""

from dataclasses import dataclass
from itertools import combinations
from typing import List

from parser.parser import Statement


@dataclass
class Redundancy:
    """Represents a detected redundancy between two statements."""

    statement_a: Statement
    statement_b: Statement
    topic: str
    action: str
    cross_document: bool

    def to_dict(self) -> dict:
        return {
            "statement_a": self.statement_a.to_dict(),
            "statement_b": self.statement_b.to_dict(),
            "topic": self.topic,
            "action": self.action,
            "cross_document": self.cross_document,
        }


def detect_redundancies(statements: List[Statement]) -> List[Redundancy]:
    """Find all pairs of statements that are redundant with each other.

    Args:
        statements: Flat list of Statement objects across all parsed
            policy documents.

    Returns:
        List of Redundancy objects.
    """
    redundancies: List[Redundancy] = []

    comparable = [
        s for s in statements
        if s.action is not None and s.topic != "GENERAL" and s.polarity in ("POSITIVE", "NEGATIVE")
    ]

    seen_pairs = set()

    for a, b in combinations(comparable, 2):
        if a.id == b.id:
            continue
        if a.topic != b.topic:
            continue
        if a.action != b.action:
            continue
        if a.polarity != b.polarity:
            continue

        # Avoid flagging near-identical duplicate text within the same file
        # as separate redundancy pairs multiple times.
        pair_key = tuple(sorted([a.id, b.id]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        redundancies.append(
            Redundancy(
                statement_a=a,
                statement_b=b,
                topic=a.topic,
                action=a.action,
                cross_document=(a.source_file != b.source_file),
            )
        )

    return redundancies
