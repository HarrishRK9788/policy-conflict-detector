"""
action_extractor.py
--------------------
Extracts the core "action" verb (or verb phrase) that a policy sentence is
regulating, e.g. rotate, encrypt, delete, retain, use, share, log, backup,
allow, deny, contain.

The extractor normalizes common inflections (rotating/rotated -> rotate,
encrypted/encrypting -> encrypt, etc.) so that two sentences referring to
the same underlying action can be compared for conflict/redundancy
detection even if their surface form differs.
"""

import re
from typing import List, Optional

# Canonical action -> list of surface-form variants / synonyms to detect.
ACTION_VARIANTS = {
    "rotate": ["rotate", "rotated", "rotating", "rotation", "changed periodically", "change periodically"],
    "encrypt": ["encrypt", "encrypted", "encrypting", "encryption"],
    "delete": ["delete", "deleted", "deleting", "deletion", "erase", "erased", "purge", "purged"],
    "retain": ["retain", "retained", "retaining", "retention", "keep", "kept", "store", "stored"],
    "use": ["use", "used", "using", "utilize", "utilized", "employ", "employed"],
    "share": ["share", "shared", "sharing", "disclose", "disclosed", "transmit", "transmitted"],
    "log": ["log", "logged", "logging", "record", "recorded"],
    "backup": ["backup", "backed up", "back up", "backing up"],
    "allow": ["allow", "allowed", "allowing", "permit", "permitted", "grant", "granted", "authorize", "authorized"],
    "deny": ["deny", "denied", "denying", "block", "blocked", "reject", "rejected", "restrict", "restricted"],
    "contain": ["contain", "contained", "containing", "isolate", "isolated", "quarantine", "quarantined"],
    "review": ["review", "reviewed", "reviewing"],
    "access": ["access", "accessed", "accessing"],
    "enable": ["enable", "enabled", "enabling"],
    "disable": ["disable", "disabled", "disabling"],
    "install": ["install", "installed", "installing"],
    "connect": ["connect", "connected", "connecting"],
}

# Build a single regex with named alternation, longest variants first so that
# e.g. "back up" matches before a shorter partial token would.
_ALL_VARIANTS_SORTED = sorted(
    ((variant, action) for action, variants in ACTION_VARIANTS.items() for variant in variants),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

_ACTION_RE = re.compile(
    r"\b(" + "|".join(re.escape(v) for v, _ in _ALL_VARIANTS_SORTED) + r")\b",
    re.IGNORECASE,
)
_VARIANT_TO_ACTION = {v.lower(): a for v, a in _ALL_VARIANTS_SORTED}


def extract_action(sentence: str) -> Optional[str]:
    """Extract the single primary canonical action from a sentence.

    Args:
        sentence: The sentence to analyze.

    Returns:
        The canonical action string (e.g. "rotate", "encrypt") or None if
        no known action verb was found.
    """
    match = _ACTION_RE.search(sentence)
    if not match:
        return None
    return _VARIANT_TO_ACTION.get(match.group(1).lower())


def extract_all_actions(sentence: str) -> List[str]:
    """Extract every distinct canonical action mentioned in a sentence."""
    actions = []
    for match in _ACTION_RE.finditer(sentence):
        canonical = _VARIANT_TO_ACTION.get(match.group(1).lower())
        if canonical and canonical not in actions:
            actions.append(canonical)
    return actions
