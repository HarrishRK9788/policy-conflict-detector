"""
classifier.py
-------------
Classifies a policy sentence into one of a fixed set of security topics
based on keyword matching. A sentence may match multiple topic keyword
sets; the topic with the most keyword hits wins. If no topic matches,
the sentence is classified as "GENERAL".
"""

import re
from typing import Dict, List

TOPICS: Dict[str, List[str]] = {
    "PASSWORD": [
        "password", "passwords", "passphrase", "credential", "credentials",
    ],
    "MFA": [
        "multi-factor", "multifactor", "mfa", "two-factor", "2fa",
        "one-time password", "otp", "authenticator",
    ],
    "ENCRYPTION": [
        "encrypt", "encryption", "encrypted", "cryptograph", "cipher",
        "tls", "ssl", "sha-1", "sha1", "md5", "aes", "key management",
    ],
    "VPN": [
        "vpn", "virtual private network", "remote access tunnel",
    ],
    "LOGGING": [
        "log", "logs", "logging", "audit trail", "siem", "event log",
    ],
    "DATA_RETENTION": [
        "retention", "retain", "archival", "archive", "purge", "dispose",
        "disposal", "delete data", "data lifecycle",
    ],
    "NETWORK": [
        "network", "firewall", "subnet", "router", "switch", "port",
        "segmentation", "intrusion", "ids", "ips",
    ],
    "ACCESS_CONTROL": [
        "access control", "least privilege", "role-based", "rbac",
        "authorization", "authorized personnel", "permission", "privilege",
    ],
    "BACKUP": [
        "backup", "backups", "back up", "disaster recovery", "restore",
        "recovery point",
    ],
}

_TOPIC_PATTERNS = {
    topic: re.compile(
        r"|".join(re.escape(kw) for kw in keywords), re.IGNORECASE
    )
    for topic, keywords in TOPICS.items()
}


def classify_topic(sentence: str) -> str:
    """Classify a sentence into a security policy topic.

    Args:
        sentence: The sentence to classify.

    Returns:
        The topic name (one of TOPICS keys) with the highest keyword hit
        count, or "GENERAL" if nothing matches.
    """
    best_topic = "GENERAL"
    best_score = 0

    for topic, keywords in TOPICS.items():
        score = sum(
            1 for kw in keywords if re.search(re.escape(kw), sentence, re.IGNORECASE)
        )
        if score > best_score:
            best_score = score
            best_topic = topic

    return best_topic


def classify_all_topics(sentence: str) -> List[str]:
    """Return every topic that has at least one keyword match (useful for tagging)."""
    matches = []
    for topic, pattern in _TOPIC_PATTERNS.items():
        if pattern.search(sentence):
            matches.append(topic)
    return matches or ["GENERAL"]
