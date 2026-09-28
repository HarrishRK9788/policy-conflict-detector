"""
analysis.py
-----------
Top-level orchestration module that ties together parsing, conflict
detection, redundancy detection, staleness detection, and graph building
into a single `run_analysis()` call used by both the web UI and the REST
API.
"""

from typing import Dict, List

from parser.parser import PolicyDocument, parse_multiple
from detector.conflict import detect_conflicts, Conflict
from detector.redundancy import detect_redundancies, Redundancy
from detector.stale import detect_all_staleness, StaleFinding
from graph.graph_builder import build_policy_graph, graph_to_json, graph_statistics


def compute_health_score(
    total_statements: int,
    conflict_count: int,
    redundancy_count: int,
    stale_doc_count: int,
    total_docs: int,
) -> int:
    """Compute a 0-100 overall policy health score.

    Deductions:
        - up to 40 points for conflicts (8 pts each, capped)
        - up to 20 points for redundancies (4 pts each, capped)
        - up to 30 points proportional to the fraction of stale documents
    """
    if total_docs == 0:
        return 100

    score = 100.0
    score -= min(conflict_count * 8, 40)
    score -= min(redundancy_count * 4, 20)
    stale_ratio = stale_doc_count / total_docs
    score -= stale_ratio * 30
    return max(0, round(score))


def run_analysis(raw_files: Dict[str, str]) -> dict:
    """Run the full analysis pipeline on a set of raw uploaded files.

    Args:
        raw_files: Mapping of filename -> raw text content.

    Returns:
        A JSON-serializable dict containing every piece of analysis output:
        documents, statements, conflicts, redundancies, staleness findings,
        graph data, and summary statistics.
    """
    documents: List[PolicyDocument] = parse_multiple(raw_files)

    all_statements = [s for doc in documents for s in doc.statements]

    conflicts: List[Conflict] = detect_conflicts(all_statements)
    redundancies: List[Redundancy] = detect_redundancies(all_statements)
    stale_findings: List[StaleFinding] = detect_all_staleness(documents)

    graph = build_policy_graph(documents, conflicts, redundancies, stale_findings)
    graph_json = graph_to_json(graph)
    graph_stats = graph_statistics(graph)

    stale_doc_count = sum(1 for f in stale_findings if f.is_stale)
    health_score = compute_health_score(
        total_statements=len(all_statements),
        conflict_count=len(conflicts),
        redundancy_count=len(redundancies),
        stale_doc_count=stale_doc_count,
        total_docs=len(documents),
    )

    topic_counts: Dict[str, int] = {}
    for s in all_statements:
        topic_counts[s.topic] = topic_counts.get(s.topic, 0) + 1

    return {
        "documents": [d.to_dict() for d in documents],
        "statements": [s.to_dict() for s in all_statements],
        "conflicts": [c.to_dict() for c in conflicts],
        "redundancies": [r.to_dict() for r in redundancies],
        "stale_findings": [f.to_dict() for f in stale_findings],
        "graph": graph_json,
        "graph_stats": graph_stats,
        "topic_counts": topic_counts,
        "summary": {
            "total_documents": len(documents),
            "total_statements": len(all_statements),
            "total_conflicts": len(conflicts),
            "total_redundancies": len(redundancies),
            "total_stale": stale_doc_count,
            "health_score": health_score,
        },
    }


def get_internal_objects(raw_files: Dict[str, str]):
    """Like run_analysis, but returns the raw Python objects (not dicts) --
    used internally by the PDF report generator which needs Statement /
    Conflict / etc. objects rather than plain dicts."""
    documents: List[PolicyDocument] = parse_multiple(raw_files)
    all_statements = [s for doc in documents for s in doc.statements]
    conflicts = detect_conflicts(all_statements)
    redundancies = detect_redundancies(all_statements)
    stale_findings = detect_all_staleness(documents)
    return documents, conflicts, redundancies, stale_findings
