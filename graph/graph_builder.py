"""
graph_builder.py
----------------
Builds a NetworkX graph representing relationships between policy
documents.

Nodes:
    One node per policy document (attributes: title, filename, stale,
    statement_count).

Edges:
    "conflict"  -> drawn between two documents that have at least one
                   conflicting statement pair between them.
    "redundant" -> drawn between two documents that have at least one
                   redundant statement pair between them.
    "related"   -> drawn between two documents that share at least one
                   topic in common but have no conflict/redundancy edge
                   already connecting them.

The resulting graph can be serialized to a JSON-friendly node/edge
structure for rendering in the browser (e.g. with vis.js / Chart.js) and
is also used to compute simple graph statistics for the dashboard.
"""

from typing import Dict, List, Set

import networkx as nx

from detector.conflict import Conflict
from detector.redundancy import Redundancy
from detector.stale import StaleFinding
from parser.parser import PolicyDocument, Statement


def build_policy_graph(
    documents: List[PolicyDocument],
    conflicts: List[Conflict],
    redundancies: List[Redundancy],
    stale_findings: List[StaleFinding],
) -> nx.MultiGraph:
    """Construct the full policy relationship graph.

    Args:
        documents: All parsed PolicyDocument objects.
        conflicts: All detected Conflict objects.
        redundancies: All detected Redundancy objects.
        stale_findings: All StaleFinding objects (used to annotate nodes).

    Returns:
        A populated networkx.MultiGraph.
    """
    graph = nx.MultiGraph()

    stale_by_file = {f.source_file: f.is_stale for f in stale_findings}

    for doc in documents:
        graph.add_node(
            doc.filename,
            title=doc.title,
            filename=doc.filename,
            is_stale=stale_by_file.get(doc.filename, False),
            statement_count=len(doc.statements),
        )

    connected_pairs: Set[frozenset] = set()

    for conflict in conflicts:
        a = conflict.statement_a.source_file
        b = conflict.statement_b.source_file
        if a == b:
            continue
        graph.add_edge(a, b, relation="conflict", topic=conflict.topic, action=conflict.action)
        connected_pairs.add(frozenset((a, b)))

    for redundancy in redundancies:
        a = redundancy.statement_a.source_file
        b = redundancy.statement_b.source_file
        if a == b:
            continue
        graph.add_edge(a, b, relation="redundant", topic=redundancy.topic, action=redundancy.action)
        connected_pairs.add(frozenset((a, b)))

    # "related" edges: documents that share a topic but aren't already
    # linked by a conflict/redundancy edge.
    topics_by_doc: Dict[str, Set[str]] = {}
    for doc in documents:
        topics_by_doc[doc.filename] = {s.topic for s in doc.statements if s.topic != "GENERAL"}

    doc_files = [doc.filename for doc in documents]
    for i in range(len(doc_files)):
        for j in range(i + 1, len(doc_files)):
            a, b = doc_files[i], doc_files[j]
            pair = frozenset((a, b))
            if pair in connected_pairs:
                continue
            shared_topics = topics_by_doc.get(a, set()) & topics_by_doc.get(b, set())
            if shared_topics:
                graph.add_edge(a, b, relation="related", topics=list(shared_topics))
                connected_pairs.add(pair)

    return graph


def graph_to_json(graph: nx.MultiGraph) -> dict:
    """Serialize the graph into a plain dict suitable for JSON responses
    and front-end visualization."""
    nodes = [
        {
            "id": node,
            "title": data.get("title", node),
            "is_stale": data.get("is_stale", False),
            "statement_count": data.get("statement_count", 0),
        }
        for node, data in graph.nodes(data=True)
    ]

    edges = [
        {
            "source": u,
            "target": v,
            "relation": data.get("relation", "related"),
            "topic": data.get("topic") or ", ".join(data.get("topics", [])),
        }
        for u, v, data in graph.edges(data=True)
    ]

    return {"nodes": nodes, "edges": edges}


def graph_statistics(graph: nx.MultiGraph) -> dict:
    """Compute a handful of simple summary statistics about the graph."""
    relation_counts = {"conflict": 0, "redundant": 0, "related": 0}
    for _, _, data in graph.edges(data=True):
        relation = data.get("relation", "related")
        relation_counts[relation] = relation_counts.get(relation, 0) + 1

    isolated = list(nx.isolates(graph))

    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "relation_counts": relation_counts,
        "isolated_documents": isolated,
        "density": round(nx.density(graph), 4) if graph.number_of_nodes() > 1 else 0.0,
    }
